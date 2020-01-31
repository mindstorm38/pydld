import traceback
import threading
import binascii
import time
import sys
import os


DEADLOCK_DETECTION_TIME = 1

delegates = []
thread = None

C_RED = u"\u001b[31m"
C_YELLOW = u"\u001b[33m"
C_RESET = "\u001b[0m"


class LockDelegate:

    def __init__(self, delegate, name=None):

        self.dl = delegate  # Delegate Lock
        self.id = binascii.hexlify(os.urandom(10)).hex()
        self.nm = name if isinstance(name, str) else self.id
        self.acqtime = 0    # Acquisition time
        self.dlck = False   # DeadLocked

        # Create Trace Hack Function Route
        self.acqroute_name = "dlr_{}".format(self.id)
        self.acqroute = None
        exec("def {0}(*args, **kwargs):\n    return self.dl.acquire(*args, **kwargs)\nself.acqroute = {0}".format(self.acqroute_name), {"self": self})

        # self.acqroute should not be None
        assert self.acqroute is not None

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def __getattr__(self, item):
        return getattr(self.dl, item)

    def acquire(self, *args, **kwargs):

        self.acqtime = time.time()
        return self.acqroute(*args, **kwargs)

    def release(self, *args, **kwargs):

        self.acqtime = 0
        return self.dl.release(*args, **kwargs)

    def is_deadlocked(self, curr_time: int):
        return self.acqtime != 0 and (curr_time - self.acqtime) > DEADLOCK_DETECTION_TIME

    def print_deadlock_info(self):

        print(C_RED)
        print("DeadLock detected for lock named '{}'...".format(self.nm))
        print(C_YELLOW, end="")

        final_frames = None

        for thid, stack in sys._current_frames().items():

            if thread is None or thid != thread.ident:

                frames = traceback.extract_stack(stack)
                frame_idx = 0

                for t in frames:

                    if t.name == self.acqroute_name:
                        final_frames = frames[0:(frame_idx-1)]  # TODO: Re-add [:-2] if needed
                        break

                    frame_idx += 1

            if final_frames is not None:
                break

        if final_frames is None:
            print("->  This lock is not the waiting one, so no traceback can be found.")
        else:

            for filename, lineno, name, line in final_frames:
                print("->  File: \"{}\", line {}, in {}".format(filename, lineno, name))
                if line:
                    print("->    {}".format(line.strip()))

        print(C_RESET)

    def __repr__(self):
        return "DeadLockDetector({}, id:{}, deadlocked:{})".format(self.nm, self.id, self.dlck)


def init_hook(only_named=False):

    if "new_producer" in (threading.Lock.__name__, threading.RLock.__name__):
        return

    def build_producer(old):
        def new_producer(*, name=None):
            if only_named and name is None:
                return old()
            else:
                global delegates
                nl = LockDelegate(old(), name)
                delegates.append(nl)
                return nl
        return new_producer

    threading.Lock = build_producer(threading.Lock)
    threading.RLock = build_producer(threading.RLock)


def check_delegates():

    while True:

        curr_time = time.time()

        for deleg in delegates:
            if not deleg.dlck and deleg.is_deadlocked(curr_time):

                deleg.dlck = True
                deleg.print_deadlock_info()

        time.sleep(DEADLOCK_DETECTION_TIME)


def start_checker():
    global thread
    thread = threading.Thread(target=check_delegates, name="DeadLock Detector Thread", daemon=True)
    thread.start()
