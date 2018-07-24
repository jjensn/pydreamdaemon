import logging
from yeelight import Bulb

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
import threading
class YeDream:

    def __init__(self, logger: object):
        self._logger = logger
        self._lights = []
        self._zones = None

        
        # 
        # FRONT RIGHT = 192.168.1.82 
        # # (zone: 11 + 0)
        # BACK RIGHT = 192.168.1.80 
        # # (zone: 2 + 3)
        # BACK CENTER = 192.168.1.83 
        # # (zone: 3 + 4 + 5)
        # BACK LEFT = 192.168.1.75 
        # # (zone: 5 + 6)
        # FRONT LEFT = 192.168.1.81 
        # # (zone: 8 + 9)
        # FRONT CENTER = 192.168.1.84 
        # # (zone: 9 + 10 + 11)
        self._FR = { 'music': 0, 'state': 1, 'r': 0, 'g': 0, 'b': 0, 'bulb': Bulb("192.168.1.82") }
        self._BR = { 'music': 0, 'state': 1, 'r': 0, 'g': 0, 'b': 0, 'bulb': Bulb("192.168.1.80") }
        self._BC = { 'music': 0, 'state': 1, 'r': 0, 'g': 0, 'b': 0, 'bulb': Bulb("192.168.1.83") }
        self._BL = { 'music': 0, 'state': 1, 'r': 0, 'g': 0, 'b': 0, 'bulb': Bulb("192.168.1.75") }
        self._FL = { 'music': 0, 'state': 1, 'r': 0, 'g': 0, 'b': 0, 'bulb': Bulb("192.168.1.81") }
        self._FC = { 'music': 0, 'state': 1, 'r': 0, 'g': 0, 'b': 0, 'bulb': Bulb("192.168.1.84") }

        self._lights.append(self._FR)
        self._lights.append(self._BR)
        self._lights.append(self._BC)
        self._lights.append(self._BL)
        self._lights.append(self._FL)
        self._lights.append(self._FC)

        self.project()

    def __exit__(self, *args):
        for light in self._lights:
            light['bulb'].stop_music()

    def project(self):
        """Set lights based on the subscription data."""
        

        zones = self._zones

        if zones == None:
            threading.Timer(5,self.project).start()
            print ("no zone!")
            return
        threading.Timer(.1,self.project).start()
        for zone, colors in zones.items():
            id = int(zone)
            r = colors['r']
            g = colors['g']
            b = colors['b']

            print ("ID %i" % id)

            index = 0 
            
            if id == 0:

            
                


                # bulb = self._lights[int(((index+1)/2)-1)]
                
                # print ("%i" , int(((index+1)/2)-1))
                # if index == 0:
                    

                index = 0
            elif id == 2:
                index = 1
            elif id == 4: 
                index = 2
            elif id == 6:
                index = 3
            elif id == 8:
                index = 4
            elif id == 10:
                index = 5
            else:
                continue
            
            self._logger.debug("%i", index)
            old_red = self._lights[index]['r']
            old_green = self._lights[index]['g']
            old_blue = self._lights[index]['b']

                    # Red Color
            color1_rgb = sRGBColor(old_red, old_green, old_blue, True)
            self._logger.debug("r g b %f %f %f", old_red, old_green, old_blue)
            # Blue Color
            color2_rgb = sRGBColor(r, g, b, True)
            self._logger.debug("r g b %f %f %f", r, g, b)

                # Convert from RGB to Lab Color Space
            color1_lab = convert_color(color1_rgb, LabColor)

            # Convert from RGB to Lab Color Space
            color2_lab = convert_color(color2_rgb, LabColor)

                # Find the color difference
            delta_e = delta_e_cie2000(color1_lab, color2_lab)
            
            if self._lights[index]['music'] == 0:
                self._lights[index]['music'] = 1
                self._lights[index]['bulb'].start_music()
            # self._logger.debug("Delta was %f!", delta_e)
           
            if (r+b+g) > 0:
                if self._lights[index]['state'] == 0:
                    self._lights[index]['bulb'].set_brightness(100)
                self._lights[index]['state'] = 1

                if delta_e >= 15.0:
                # if self._lights[index]['state'] == 0:
                #     self._lights[index]['state'] = 1
                #     self._lights[index]['bulb'].set_brightness(100)
                    self._lights[index]['r'] = r
                    self._lights[index]['g'] = g
                    self._lights[index]['b'] = b

                    self._lights[index]['bulb'].set_rgb(r, g, b)
                
            else :
                self._lights[index]['r'] = r
                self._lights[index]['g'] = g
                self._lights[index]['b'] = b
                if self._lights[index]['state'] == 1:
                    # self._lights[index]['bulb'].turn_off()
                    self._lights[index]['bulb'].set_brightness(1)
                self._lights[index]['state'] = 0
                    
                # threading.Timer(0.01,self.project).start()
            # elif index == 2:
            #     self._BR.set_rgb(r, g, b)
            # elif index == 4:
            #     self._BC.set_rgb(r, g, b)
            # elif index == 6
            #     self._BL.set_rgb(r, g, b)
            # elif index == 8
            #     self._FL.set_rgb(r, g, b)
            # elif index == 10
            #     self._FC.set_rgb(r, g, b)
    
#         print ("%i r %s g %s b %s" % (key, value['r'],value['g'],value['b'] ))
