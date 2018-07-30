import logging, yaml, copy
from yeelight import Bulb

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
import threading

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
    def __init__(self, config_path):
        self._logger = logging.getLogger(__name__)
        self._bulbs = []
        self._config_path = config_path

        self.zone_data = None

        try:
            config_file = open(config_path)
            self._settings = yaml.safe_load(config_file)
            config_file.close()

        except:
            self._logger.error("Failed to load configuration file %s, are you sure it exists?", config_path)
            exit(2)

        for light in list(self._settings["bulbs"]):
            light["state"] = state
            self._bulbs.append(Bulb(light["ip"], port=55443, effect=self._settings["settings"]["effect"], duration=self._settings["settings"]["duration"], auto_on=False))

        self._init_bulbs(self._bulbs)
        self.project()

    def __exit__(self, *args):
        self._logger.info("Exiting...")
        for bulb in list(self._bulbs):
            bulb['bulb'].stop_music()

    def _config_loop(self):
        threading.Timer(10, self._config_loop).start()
        try:
            config_file = open(self._config_path)
            new_settings = yaml.safe_load(config_file)
            self._settings.config = new_settings.config
            config_file.close()
        
        except:
            self._logger.error("Failed to load configuration file %s, are you sure it exists?", self._config_path)
            exit(2)

    def _init_bulbs(self, bulbs):
        for idx,light in enumerate(bulbs):
            yeelight = light
            yeelight.get_properties()
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

            brightness_thread = threading.Thread(target=light.set_brightness, args=[100]) 
            brightness_thread.start()
        
    def project(self):
        """Set lights based on the subscription data."""
        zones = self.zone_data

        if zones == None:
            self._logger.info("Have not received any zone data from a DreamScreen device, sleeping...")
            threading.Timer(5, self.project).start()
            return

        threading.Timer(.125, self.project).start()

        settings_copy = copy.deepcopy(self._settings)
        for idx, bulb in enumerate(settings_copy["bulbs"]):
            # print ("%s %s", bulb["name"], bulb.get("state")["power"])
            zone_count = 0
            r = 0
            b = 0
            g = 0

            for target_zone in list(bulb["zones"]):
                zone_count = zone_count + 1
                zone = self.zone_data.get(int(target_zone - 1))
                r = r + zone['r']
                g = g + zone['g']
                b = b + zone['b']
            
            if zone_count > 0:
                r = int(r / zone_count)
                g = int(g / zone_count)
                b = int(b / zone_count)

            # self._logger.info("Average zone color for bulb %s: [ %i %i %i ]", bulb["name"], r, g, b)

            if r + b + g >= 10:
                curr_colors = bulb.get("state")["colors"]

                curr_rgb = sRGBColor(curr_colors["r"], curr_colors["g"], curr_colors["b"], True)
                new_rgb = sRGBColor(r, g, b, True)

                curr_lab = convert_color(curr_rgb, LabColor)
                new_lab = convert_color(new_rgb, LabColor)

                delta = delta_e_cie2000(curr_lab, new_lab)
                # self._logger.info("Delta for zone %s: [ %i ]", bulb["name"], delta)
                if delta >= self._settings["settings"]["sensitivity"]:
                    self._settings["bulbs"][idx]["state"]["power"] = "on"
                    self._settings["bulbs"][idx]["state"]["colors"]["r"] = r
                    self._settings["bulbs"][idx]["state"]["colors"]["g"] = g
                    self._settings["bulbs"][idx]["state"]["colors"]["b"] = b
                    # self._logger.info("Changing zone %s: [ %i ]", bulb["name"], delta)
                    if bulb.get("state")["power"] == "on":
                        self._bulbs[idx].set_brightness(int(self._settings["settings"]["max_brightness"]))
                    
                    color_thread = threading.Thread(target=self._bulbs[idx].set_rgb, args=[r, g, b])  # <- 1 element list
                    color_thread.start()

            else:
                self._settings["bulbs"][idx]["state"]["power"] = "off"
            
                if bulb.get("state")["power"] == "on":
                    self._bulbs[idx].set_brightness(1)