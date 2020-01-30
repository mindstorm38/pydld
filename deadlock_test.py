import deadlock_detector
deadlock_detector.init_hook(only_named=True)
deadlock_detector.start_checker()

import threading
import time

if __name__ == '__main__':

    l1 = threading.Lock(name="l1")
    l2 = threading.Lock(name="l2")

    while True:

        print("Main tick ...")

        with l1:
            with l2:
                with l1:
                    pass

        time.sleep(1)
