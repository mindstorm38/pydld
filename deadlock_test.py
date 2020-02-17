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
            print("L1 acquired")
            with l2:
                print("L2 acquired")
                with l1:
                    print("L1 acquired")
                    pass

        """with l1:
            print("L1 acquired")
            with l1:
                print("L1 acquired")"""

        """
        l1.acquire()
        l2.acquire()
        l1.acquire()
        l1.release()
        l2.release()
        l1.release()
        """

        time.sleep(1)
