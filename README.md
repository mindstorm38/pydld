# Python DeadLock Detector

This is a utility library for python scripts. It simply hooks into `threading` module and change the `Lock` and `RLock` functions to return a custom object that can be automatically checked by a separate thread.

## Usage

To work efficiently on all your modules you have to init hook and start the thread at the very beginning of your main script.

You can check out the `deadlock_test.py` example file to understand where import is needed.

The custom `Lock` and `RLock` function have an optional parameter `name`, it is usefull to recognize the lock faster if deadlock is detected.

In addition to that, the module `init_hook` function has an optional parameter `only_named` that force use the default behaviour of `Lock` and `RLock` functions if parameter `name` is not specified. It can be usefull if you want to profile only specific locks.

> This library is forced to create temporary python modules in order to "hack" the python traceback.
> These modules are stored in a directory named 'trace_hacks' in the same directory as the `deadlock_detector` module, it is created automatically and cleared before every new launch.