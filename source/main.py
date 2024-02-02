from common.service import Service
from typing import List

import beatmaps.service as beatmaps_svc
import common.app as app
import logging
import signal
import sys

class ServiceHandler:
    
    logger = logging.getLogger("ServiceHandler")
    def __init__(self) -> None:
        self.services: List[Service] = self.get_services()
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        app.STOPPED = True
    
    def get_services(self):
        # TODO: disable services based on config
        return [beatmaps_svc.get_service()]
    
    def run(self):
        for service in self.services:
            service.thread.start()
        for service in self.services:
            service.thread.join()
            self.logger.warning(f"Service {service.service_name} exited!")
        sys.exit(0)

if __name__ == '__main__':
    ServiceHandler().run()