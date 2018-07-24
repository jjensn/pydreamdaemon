import datetime
import logging
import socket
import sys
import socketserver
import crc8
import json

import redis

from typing import Union, Dict, List, Generator
from threading import Thread, Timer

from yedream import YeDream

class MessageManager:
    """Communicate with DreamScreen devices."""

    @property
    def subscription(self) -> bool:
        """Subscribe to DreamScreen color feed."""
        return self._subscription

    @subscription.setter
    def subscription(self, value: bool) -> None:
        """Subscribe to DreamScreen color feed."""
        if not isinstance(value, bool):
            raise TypeError("Expected bool got {}".format(type(value)))
        else:
            self._logger.debug("setting subscription to %i", value)
            
            self._subscription = value

            # if self._subscription == True:
            #     self._sub_keep_alive.start()
            # elif self._subscription == False:
            #     self._sub_keep_alive.cancel()

    def __init__(self, config:str, redis_host: str = "localhost"):
        """Setup udp listener."""

        self._subscription = False
        self._logger = logging.getLogger(__name__)
        self._listener = Thread(target=self.listen, args=())
        self._stop_listening = False
        self._yedream = YeDream(config)
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET,
                               socket.SO_BROADCAST,
                               1)

        # self._q = redis.StrictRedis(host=redis_host, port=6379, db=0)
        # self._q.pubsub()

        self.socket.bind(('', 8888))

        self._logger.debug("Initialized MessageManager")

    def start(self):
        """Start the listener thread."""
        self._stop_listening = False
        self._logger.debug("Starting listener")
        self._listener.start()
        self._logger.debug("Success!")

    def stop(self):
        """Tell the listener to stop listening."""
        self._should_stop = True

    def listen(self):
        """Wait for broadcast messages."""
        try:
            while True:
                if self._stop_listening == True:
                    self._logger.debug("Received stop message...stopping...")
                    return
                message, address = self.socket.recvfrom(1024)
                ip, port = address
                if port == 8888:
                    if message[0:6] == b"\xfc\x91\xff`\x01\n":
                        self._logger.debug("Received a status message from %s", ip)
                    elif message[0:7] == b"\xfc\x05\x01\x30\x01\x0c\xff":
                        self._logger.debug("Received a subscription request")
                        if self._subscription == True:
                            self._logger.debug("Sending a keep alive message!")
                            self._send_packet('255.255.255.255', self._generate_subscription_packet(1), True)
                    elif message[0:2] == b"\xfc\x29" and message[4:6] == b"\x03\x16":
                        if self._subscription == True:
                            # self._logger.debug("Received a color stream from %s", ip)
                            self._parse_color_sections(message[6:])
                    else:
                        self._logger.debug("Unknown message %s", message)
        except socket.timeout:
            return

    def _generate_subscription_packet(self, group: int) -> bytearray:
        """Generate a subscription packet."""
        flags = 48
        namespace = 1
        command = 12
        payload = [1]

        packet = self._build_packet(namespace, command, group, flags, payload)

        self._logger.debug("Subscription %s", packet)

        return packet

    def _send_packet(self, ip: str, data: bytearray, broadcast: bool = False) -> bool:
        """Send a packet to DreamScreen devices."""
        if not isinstance(data, bytearray):
            self._logger.error("packet type %s != bytearray", type(data))
            return False

        if broadcast:
            self.socket.sendto(data, ('255.255.255.255', 8888))
        else:
            self.socket.sendto(data, (ip, 8888))
        
        return True

    @staticmethod
    def _crc8(data: bytearray) -> bytes:
        message_hash = crc8.crc8()
        message_hash.update(data)
        return message_hash.digest()

    def _build_packet(self, namespace: int, command: int, group_number: int, flags: int, payload: Union[List, tuple]) \
            -> bytearray:
        """Build a packet that DreamScreen can understand."""
        if not isinstance(payload, (list, tuple)):
            self._logger.error("payload type %s != list|tuple", type(payload))
            
        # if namespace == 1 and command == 12:
        #     # Subscribe [ 0x1 , 0xC ]
        #     flags = 48 # 0x30
        # else:
        #     if self.group_number == 0:
        #         flags = 17
        #     else:
        #         flags = 33
        
        resp = [252,
                len(payload) + 5,
                group_number,
                flags,
                namespace,
                command]
        resp.extend(payload)
        resp.extend(self._crc8(bytearray(resp)))
        
        return bytearray(resp)

    def _parse_color_sections(self, message: bytes) -> Dict[int, Dict]:
            """Take a color subscription payload and convert to dictionary. """
            ret = {}
            for count, element in enumerate(list(message), 0):
                if (count + 1) % 3 == 0:
                    index = int(count / 3)
                    # print ("cont %i", index)
                    red = int(count - 2)
                    green = int(red + 1)
                    blue = int(green + 1)
                    
                    ret[index] = {
                        "r": int.from_bytes(message[red:green], byteorder='big', signed=False),
                        "g": int.from_bytes(message[green:blue], byteorder='big', signed=False),
                        "b": int.from_bytes(message[blue:blue + 1], byteorder='big', signed=False)
                    }
 
            # self._q.publish("sidekick", json.dumps(ret))
            self._yedream.zone_data = ret




# def process_values(color_data: Dict):
#     print ("%s", color_data)
#     for key, value in color_data.items():
#         print ("%i r %s g %s b %s" % (key, value['r'],value['g'],value['b'] ))