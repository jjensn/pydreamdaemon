import logging, yaml, copy, threading, redis, json
import cv2, math, time, colorsys
import numpy as np

from yeelight import Bulb
from yeelight import discover_bulbs

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
from sklearn.cluster import KMeans

state = { 
    'power': 'on',
    'music_mode': 0,
    'colors': {
        'r': 0,
        'g': 0,
        'b': 0
    },
    'brightness': 0
}

class YeDream:
    def __init__(self, config, pool, debug):
        self._logger = logging.getLogger(__name__)
        self._bulbs = []

        self._settings = config
        self._redis = redis.Redis(connection_pool=pool)
        self._pubsub = self._redis.pubsub()
        self._pubthread = None
        
        for light in list(self._settings["bulbs"]):
            light["state"] = state
            self._bulbs.append(Bulb(light["ip"], effect=self._settings["settings"]["effect"], duration=self._settings["settings"]["duration"], auto_on=False, power_mode=3))

        # if not debug:
        self._init_bulbs(self._bulbs)

        self._pubsub.subscribe(**{'dream-data': self.process_frame})
        self._pubthread = self._pubsub.run_in_thread(sleep_time=0.001)

    def __exit__(self, *args):
        self._logger.info("Received shutdown command...")
        self._pubthread.stop()
        for bulb in list(self._bulbs):
            bulb['bulb'].stop_music()
        
        self._pubthread.stop()

    def _init_bulbs(self, bulbs):
        discover_bulbs(timeout=2, interface=False)
        for idx,light in enumerate(bulbs):
            yeelight = light

            yeelight.get_properties()

            if yeelight.last_properties.get("power") == "off":
                yeelight.toggle(effect="sudden")

            self._settings["bulbs"][idx]["state"]["power"] = yeelight.last_properties.get("power")

            rgb = int(yeelight.last_properties.get("rgb"))
            blue = rgb & 0xff
            green = (rgb >> 8) & 0xff
            red = (rgb >> 16) & 0xff

            self._settings["bulbs"][idx]["state"]["colors"]["r"] = red
            self._settings["bulbs"][idx]["state"]["colors"]["g"] = green
            self._settings["bulbs"][idx]["state"]["colors"]["b"] = blue

            yeelight.start_music()
            self._settings["bulbs"][idx]["state"]["music_mode"] = 1

            # brightness_thread = threading.Thread(target=light.set_brightness, args=[int(self._settings["settings"]["max_brightness"])])  # <- 1 element list
            # brightness_thread.start()

    def _combine_zones(self, frame) -> []:
        colors = []
        r,g,b = (0,0,0)

        for zone in range(len(frame)):
            colors.append( (frame[str(zone)]['r'], frame[str(zone)]['g'], frame[str(zone)]['b']) )
            r += int(frame[str(zone)]['r'])
            g += int(frame[str(zone)]['g'])
            b += int(frame[str(zone)]['b'])
        
        # average the colors
        r /= len(frame)
        g /= len(frame)
        b /= len(frame)
    
        return colors

    def _create_histogram(self, clt):
        numLabels = np.arange(0, len(np.unique(clt.labels_)) + 1)
        (hist, _) = np.histogram(clt.labels_, bins = numLabels)
        hist = hist.astype("float")
        hist /= hist.sum()
        return hist

    def _cluster_colors(self, colors):
        clt = KMeans(n_clusters=3)
        clt.fit(colors)
        hist = self._create_histogram(clt)

        return sorted(zip(hist, clt.cluster_centers_),key=lambda x: x[0],reverse=True)

    def _calc_brightness(self, color) -> int:
        return math.sqrt( 0.299*pow(color[0],2) + 0.587*pow(color[1],2) + 0.114*pow(color[2],2) ) 

    def _project(self, cluster):
        """Decide which bulbs should show which colors (or be toggled off)."""
        if cluster is not None:
            # we have valid color clusters (ie: the frame is not black)

            brightest_color = None
            brightest = 0

            (percent, color) = cluster[0]

            if percent > 0.8 and self._calc_brightness(color) < 25:
                print("TURNING OFF")
                for i in range(6):
                    if self._bulbs[i].last_properties.get("power") == "on":
                        #self._bulbs[i].toggle(effect="sudden")
                        self._bulbs[i].set_brightness(0)
            else:
                for (percent, color) in cluster:
                    # use the brightest color instead of the most represented color
                    # (it looks better)
                    brightness = int((self._calc_brightness(color)))

                    if brightness > brightest:
                        brightest_color = color
                        brightest = brightness

                if brightest == 0:
                    return

                for i in range(6):
                    # convert the color to hsv (yeelight api works better with hsv over rgb)

                    # if self._bulbs[i].last_properties.get("power") == "off":
                    #     self._bulbs[i].toggle()
                    
                    
                    r = brightest_color[0]/255
                    g = brightest_color[1]/255
                    b = brightest_color[2]/255

                    hsv = colorsys.rgb_to_hsv(r,g,b)
                    # self._bulbs[i].start_music()
                    # self._bulbs[i].turn_on()
                    # self._bulbs[i].turn_on()
                    # TODO: update the config to support brightness adjustment
#                     if i < 2:
#                         try:
#                             self._bulbs[i].set_hsv(hsv[0]*360, hsv[1]*100, 25)
#                         except:
#                             self._bulbs[i].toggle()
#                             self._bulbs[i].get_properties()
#                     else:
                    try:
                        self._bulbs[i].set_hsv(hsv[0]*360, hsv[1]*100, self._settings["settings"]["max_brightness"])
                    except:
                        self._bulbs[i].toggle()
                        self._bulbs[i].get_properties()


    def process_frame(self, message):
        """Load DreamScreen data into an object and perform color calculations."""
        clustered_colors = None

        frame = json.loads(message['data'])
        colors = self._combine_zones(frame)

        if colors is None:
            # running all black through the clustering function causes the application to hang
            self._logger.info("Majority of frame is black; diming lights instead of updating colors")
            clustered_colors = None
        else:
            clustered_colors = self._cluster_colors(colors)
        
        self._project(clustered_colors)