from common.logging import get_logger
from common.service import Service
from typing import List

import beatmaps.service as beatmaps_svc
import tracker.service as tracker_svc
import common.app as app
import signal
import sys

class ServiceHandler:
    
    logger = get_logger("svc_handler")
    def __init__(self) -> None:
        self.services: List[Service] = self.get_services()
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        app.STOPPED = True
    
    def get_services(self):
        # TODO: disable services based on config
        services = [beatmaps_svc.get_service()]
        services.extend(tracker_svc.get_services())
        return services

    def run(self):
        for service in self.services:
            service.thread.start()
        for service in self.services:
            while True:
                service.thread.join(timeout=5)
                if not service.thread.is_alive():
                    break
            self.logger.warning(f"Service {service.service_name} exited!")
        sys.exit(0)

if __name__ == '__main__':
    ServiceHandler().run()