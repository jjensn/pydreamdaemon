import logging, yaml
from yeelight import Bulb

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
import threading

state = { 
    'power': 'off',
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
            # threading.Timer(10, self._config_loop).start()

        except:
            self._logger.error("Failed to load configuration file %s, are you sure it exists?", config_path)
            exit(2)

        for light in self._settings["bulbs"]:
            light["state"] = state
            light["object"] = Bulb(light["ip"], port=55443, effect=self._settings["settings"]["effect"], duration=self._settings["settings"]["duration"], auto_on=False)

        self._init_bulbs(self._settings["bulbs"])
        self.project()

    def __exit__(self, *args):
        for bulb in self._bulbs:
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
        for light in bulbs:
            yeelight = light.get("object")
            yeelight.get_properties()
            light.get("state")["power"] = yeelight.last_properties.get("power")
            light.get("state")["brightness"] = yeelight.last_properties.get("brightness")

            rgb = int(yeelight.last_properties.get("rgb"))
            blue = rgb & 0xff
            green = (rgb >> 8) & 0xff
            red = (rgb >> 16) & 0xff

            light.get("state")["colors"]["r"] = red
            light.get("state")["colors"]["g"] = green
            light.get("state")["colors"]["b"] = blue

            yeelight.start_music()
            light.get("state")["music_mode"] = 1

    def project(self):
        """Set lights based on the subscription data."""

        c = self._settings
        zones = self.zone_data

        if zones == None:
            self._logger.info("Have not received any zone data from a DreamScreen device, sleeping...")
            threading.Timer(5, self.project).start()
            return

        #threading.Timer(float(c["settings"]["update_rate"]), self.project).start()
        threading.Timer(.25, self.project).start()
        # for zone, colors in zones.items():
        for bulb in c["bulbs"]:

            zone_count = 0
            r = 0
            b = 0
            g = 0

            for target_zone in bulb["zones"]:
                zone_count = zone_count + 1
                zone = self.zone_data.get(int(target_zone - 1))
                r = r + zone['r']
                g = g + zone['g']
                b = b + zone['b']
            
            if zone_count > 0:
                r = int(r / zone_count)
                g = int(g / zone_count)
                b = int(b / zone_count)

            self._logger.info("Average zone color for bulb %s: [ %i %i %i ]", bulb["name"], r, g, b)

            if r + b + g >= 25:
                curr_colors = bulb.get("state")["colors"]
                curr_rgb = sRGBColor(curr_colors["r"], curr_colors["g"], curr_colors["b"], True)
                # self._logger.debug("r g b %f %f %f", old_red, old_green, old_blue)
                # Blue Color
                new_rgb = sRGBColor(r, g, b, True)
                # self._logger.debug("r g b %f %f %f", r, g, b)

                curr_lab = convert_color(curr_rgb, LabColor)
                new_lab = convert_color(new_rgb, LabColor)

                delta = delta_e_cie2000(curr_lab, new_lab)
                self._logger.info("Delta for zone %s: [ %i ]", bulb["name"], delta)
                if delta >= c["settings"]["sensitivity"]:
                    # if bulb.get("state")["power"] == "off":
                        # bulb.get("object").turn_on()
                        # bulb.get("object").set_brightness(c["settings"]["max_brightness"])
                        # bulb.get("object").turn_on()
                    bulb.get("state")["power"] = "on"

                    bulb.get("state")["colors"]["r"] = r
                    bulb.get("state")["colors"]["g"] = g
                    bulb.get("state")["colors"]["b"] = b
                    self._logger.info("Changing zone %s: [ %i ]", bulb["name"], delta)
                    processThread = threading.Thread(target=bulb.get("object").set_rgb, args=[r, g, b])  # <- 1 element list
                    processThread.start()

                    # bulb.get("object").set_rgb(r, g, b)

            # else:
                # if bulb.get("state")["power"] == "on":
                    # bulb.get("object").turn_off()
                # bulb.get("state")["power"] = "off"

            # for bulb in c.config.bulbs:

            
            # if id == 0:

            
                


            #     # bulb = self._lights[int(((index+1)/2)-1)]
                
            #     # print ("%i" , int(((index+1)/2)-1))
            #     # if index == 0:
                    

            #     index = 0
            # elif id == 2:
            #     index = 1
            # elif id == 4: 
            #     index = 5
            # elif id == 6:
            #     index = 3
            # elif id == 8:
            #     index = 4
            # elif id == 10:
            #     index = 2
            # else:
            #     continue
            
            # self._logger.debug("%i", index)


            # if self._lights[index]['music'] == 0:
            #     self._lights[index]['bulb'].get_properties()
            #     self._lights[index]['state'] = self._lights[index]['bulb'].last_properties.get('power')
            #     self._lights[index]['music'] = 1
            #     self._lights[index]['bulb'].start_music()


            # old_red = self._lights[index]['r']
            # old_green = self._lights[index]['g']
            # old_blue = self._lights[index]['b']

            #         # Red Color
            # color1_rgb = sRGBColor(old_red, old_green, old_blue, True)
            # self._logger.debug("r g b %f %f %f", old_red, old_green, old_blue)
            # # Blue Color
            # color2_rgb = sRGBColor(r, g, b, True)
            # self._logger.debug("r g b %f %f %f", r, g, b)

            #     # Convert from RGB to Lab Color Space
            # color1_lab = convert_color(color1_rgb, LabColor)

            # # Convert from RGB to Lab Color Space
            # color2_lab = convert_color(color2_rgb, LabColor)

            #     # Find the color difference
            # delta_e = delta_e_cie2000(color1_lab, color2_lab)
            
            
            # # self._logger.debug("Delta was %f!", delta_e)
           
            # if (r+b+g) > 25:
            #     if self._lights[index]['state'] == 0 or self._lights[index]['state'] == 'off':
            #         self._lights[index]['bulb'].set_brightness(75)
            #     self._lights[index]['state'] = 1

            #     if delta_e >= 15.0:
            #     # if self._lights[index]['state'] == 0:
            #     #     self._lights[index]['state'] = 1
            #     #     self._lights[index]['bulb'].set_brightness(100)
            #         self._lights[index]['r'] = r
            #         self._lights[index]['g'] = g
            #         self._lights[index]['b'] = b

            #         self._lights[index]['bulb'].set_rgb(r, g, b)
                
            # else :
            #     # self._lights[index]['r'] = r
            #     # self._lights[index]['g'] = g
            #     # self._lights[index]['b'] = b
            #     if self._lights[index]['state'] == 1 or self._lights[index]['state'] == 'on':
            #         # self._lights[index]['bulb'].turn_off()
            #         self._lights[index]['bulb'].set_brightness(1)
            #     self._lights[index]['state'] = 0
                    
            #     # threading.Timer(0.01,self.project).start()
            # # elif index == 2:
            # #     self._BR.set_rgb(r, g, b)
            # # elif index == 4:
            # #     self._BC.set_rgb(r, g, b)
            # # elif index == 6
            # #     self._BL.set_rgb(r, g, b)
            # # elif index == 8
            # #     self._FL.set_rgb(r, g, b)
            # # elif index == 10
            #     self._FC.set_rgb(r, g, b)
    
#         print ("%i r %s g %s b %s" % (key, value['r'],value['g'],value['b'] ))
