import logging

from messagemanager import MessageManager

def main():
    _LOGGER = logging.getLogger(__name__)

    logging.basicConfig(level=logging.DEBUG)
    manager = MessageManager(_LOGGER)

    manager.start()

    manager.subscription = True

if __name__ == '__main__':
    main()