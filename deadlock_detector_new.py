from weakref import WeakSet
import traceback
import threading
import time
import sys

from typing import Optional, Callable, Any, Iterable, Union


__all__ = [
    "init",
    "OldLock", "OldRLock",
    "deadlock_detection_time",
    "print_callback"
]


OldLock = threading.Lock
OldRLock = threading.RLock


deadlock_detection_time = 4     # type: int
print_callback = print          # type: Callable[[Any], None]


_thread = None                  # type: Optional[threading.Thread]
_all = WeakSet()                # type: Union[WeakSet, Iterable[DLock]]
_all_lck = OldLock()


class DLock:

    def __init__(self, lock):

        self.lck = lock

        # Last acquisition timestamp
        self.lac = 0

        # Already deadlocked
        self.dld = False

        # Retreive definition frame
        self.dfr = traceback.extract_stack()[-3]
        # self.pos = "\"{}\", line {}, in {}".format(dfr.filename, dfr.lineno, dfr.name)

        # Acquire route, used to check
        self.arf = None
        self.arn = "_{}".format(id(self))
        exec("def {0}(*args, **kwargs):\n    return s.lck.acquire(*args, **kwargs)\ns.arf = {0}".format(self.arn), {"s": self})

        assert callable(self.arf)

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def __getattr__(self, item):
        return getattr(self.lck, item)

    def acquire(self, *args, **kwargs):
        self.lac = time.monotonic()
        return self.arf(*args, **kwargs)

    def release(self, *args, **kwargs):
        self.lac = 0
        return self.lck.release(*args, **kwargs)

    def is_deadlocked(self, curr_time: float) -> bool:
        return self.lac != 0 and (curr_time - self.lac) > deadlock_detection_time

    def get_final_frames(self):
        for thid, stack in sys._current_frames().items():
            if _thread is None or thid != _thread.ident:
                frames = traceback.extract_stack(stack)
                for t in frames:
                    if t.name == self.arn:
                        try:
                            th = str(next((th for th in threading.enumerate() if th.ident == thid)))
                        except StopIteration:
                            th = "<invalid thread>"
                        return frames[:-2], th
        return None, None

    def print_deadlock_info(self):

        final_frames, final_thread = self.get_final_frames()

        print_callback("")
        print_callback("### DeadLock Information ###")

        print_callback(" -> Lock defined at \"{}\", line {}, in {}".format(self.dfr.filename, self.dfr.lineno, self.dfr.name))
        if self.dfr.line:
            print_callback(" ->    {}".format(self.dfr.line.strip()))

        if final_frames is None:
            print_callback(" -> This lock is not the waiting one, so no traceback can be found.")
        else:
            print_callback(" -> Locked in thread '{}'".format(final_thread))
            for filename, lineno, name, line in final_frames:
                print_callback(" ->  \"{}\", line {}, in {}".format(filename, lineno, name))
                if line:
                    print_callback(" ->    {}".format(line.strip()))

        print_callback("")


def _check():
    while True:
        curr_time = time.monotonic()
        with _all_lck:
            for dlck in _all:
                if not dlck.dld and dlck.is_deadlocked(curr_time):
                    dlck.dld = True
                    dlck.print_deadlock_info()
        time.sleep(deadlock_detection_time)


def init():

    global _thread

    if _thread is not None or "new_producer" in (threading.Lock.__name__, threading.RLock.__name__):
        return

    def build_producer(old):
        def new_producer():
            lck = DLock(old())
            with _all_lck:
                _all.add(lck)
            return lck
        return new_producer

    threading.Lock = build_producer(threading.Lock)
    threading.RLock = build_producer(threading.RLock)

    _thread = threading.Thread(target=_check, name="DeadLock Detector Thread", daemon=True)
    _thread.start()
