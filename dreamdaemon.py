import logging, time
import yaml
import argparse
import redis

# from yedebug import YeDebug
from yedream import YeDream

from messagemanager import MessageManager

def main():
    _LOGGER = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-C", "--config", help="path to config file", type=str)
    args = parser.parse_args()

    if not args.config:
        _LOGGER.error(">> Configuration file required, pass it with '-c <file>'")
        _LOGGER.error(">> python dreamscreen.py -c config.yml")
        exit(1)

    try:
        config_file = open(args.config)
        settings = yaml.safe_load(config_file)
        config_file.close()
    except:
        _LOGGER.error("Failed to load configuration file %s, are you sure it exists?", args.config)
        exit(2)

    p = redis.ConnectionPool(host='localhost', port=6379, db=0)

    dream = YeDream(config=settings, pool=p, debug=True)

    # debug = YeDebug(config=settings, pool=p)

    # debug.start()

    # while True:
        # time.sleep(1)

    manager = MessageManager(config=settings, pool=p)

    manager.start()

    manager.subscription = True
    

if __name__ == '__main__':
    main()