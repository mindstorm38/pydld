from threading import Thread
import threading

from typing import Union


OldLock = threading.Lock
OldRLock = threading.RLock


class DLock:

    __slots__ = "lck",

    all = []
    all_lck = OldLock()

    def __init__(self, lock):
        self.lck = lock


def init():

    def build_producer(old):
        def new_producer():
            return DLock(old())
        return new_producer

    threading.Lock = build_producer(threading.Lock)
    threading.RLock = build_producer(threading.RLock)
