import logging
import yaml
import argparse

from messagemanager import MessageManager

def main():
    _LOGGER = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="path to config file", type=str)
    args = parser.parse_args()

    if not args.config:
        _LOGGER.error(">> Configuration file required, pass it with '-c <file>'")
        _LOGGER.error(">> python dreamscreen.py -c config.yml")
        exit(1)

    manager = MessageManager(args.config)

    manager.start()

    manager.subscription = True
    

if __name__ == '__main__':
    main()