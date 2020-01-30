from importlib import import_module
from os import path
import traceback
import threading
import binascii
import shutil
import time
import sys
import os


RUNNING_DIR = path.dirname(__file__)

DEADLOCK_DETECTION_TIME = 1
TRACE_HACK_PATTERN_FILE = path.join(RUNNING_DIR, "trace_hack.py")
TRACE_HACK_DIRECTORY = path.join(RUNNING_DIR, "trace_hacks")

delegates = []
thread = None

C_RED = u"\u001b[31m"
C_YELLOW = u"\u001b[33m"
C_RESET = "\u001b[0m"


class LockDelegate:

    def __init__(self, delegate, name=None):

        self.dl = delegate  # Delegate Lock
        self.nm = name if isinstance(name, str) else None
        self.id = binascii.hexlify(os.urandom(16)).hex()
        self.acqtime = 0    # Acquisition time
        self.dlck = False   # DeadLocked

        # Trace hack
        if self.nm is not None:
            self.thck_file = path.join(TRACE_HACK_DIRECTORY, "th_{}.py".format(self.id))
            shutil.copyfile(TRACE_HACK_PATTERN_FILE, self.thck_file)
        else:
            self.thck_file = None

        self.thck_mod = None

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self, *args, **kwargs):

        self.acqtime = time.time()

        if self.thck_file is not None:
            self.thck_mod = import_module("th_{}".format(self.id))  # Can directly import since trace_hacks directory is added to path

        if self.thck_mod is not None:
            self.thck_mod.route(self.dl.acquire, *args, **kwargs)
        else:
            self.dl.acquire(*args, **kwargs)

    def release(self, *args, **kwargs):
        self.dl.release(*args, **kwargs)
        self.acqtime = 0

    def is_deadlocked(self, curr_time: int):
        return self.acqtime != 0 and (curr_time - self.acqtime) > DEADLOCK_DETECTION_TIME

    def print_deadlock_info(self):

        print(C_RED)
        print("DeadLock detected for lock named '{}'...".format(self.nm))
        print(C_YELLOW, end="")

        if self.thck_file is not None:

            final_frames = None

            for thid, stack in sys._current_frames().items():

                if thread is None or thid != thread.ident:
                    frames = traceback.extract_stack(stack)
                    for t in traceback.extract_stack(stack):
                        if path.normpath(t.filename) == self.thck_file:
                            final_frames = frames[:-2]
                            break

                if final_frames is not None:
                    break

            if final_frames is None:
                print("=> This lock is not the waiting one, so no traceback can be found.")
            else:

                for filename, lineno, name, line in final_frames:
                    print("=> File: \"{}\", line {}, in {}".format(filename, lineno, name))
                    if line:
                        print("=>   {}".format(line.strip()))
        else:
            print("=> Trace back information disabled, specify 'name' parameter when creating the lock.")

        print(C_RESET)

    def __repr__(self):
        return "DeadLockDetector({}, id:{}, deadlocked:{})".format(self.nm, self.id, self.dlck)


def init_hook(only_named=False):

    if path.isdir(TRACE_HACK_DIRECTORY):
        shutil.rmtree(TRACE_HACK_DIRECTORY)

    os.mkdir(TRACE_HACK_DIRECTORY)
    sys.path.append(TRACE_HACK_DIRECTORY)

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
