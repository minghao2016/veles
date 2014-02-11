"""
Created on Jan 31, 2014

@author: Vadim Markovtsev <v.markovtsev@samsung.com>
"""


import logging
import multiprocessing as mp
import os
import queue
import time

import config


class Graphics(object):
    """ Class handling all interaction with main graphics window
        NOTE: This class should be created ONLY within one thread
        (preferably main)

    Attributes:
        _instance: instance of Graphics class. Used for implementing
            Singleton pattern for this class.
        root: TKinter graphics root.
        event_queue: Queue of all pending changes created by other threads.
        run_lock: Lock to determine whether graphics window is running
        registered_plotters: List of registered plotters
        is_initialized: whether this class was already initialized.
    """

    _instance = None
    event_queue = None
    process = None
    interval = 0.1  # secs in event loop

    @staticmethod
    def initialize():
        if not Graphics.process:
            Graphics.event_queue = mp.Queue(100)  # to prevent infinite queue
            """ TODO(v.markovtsev): solve the problem with matplotlib, ssh and
            multiprocessing - hangs on figure.show()
            """
            import socket
            if socket.gethostname() == "smaug":
                import threading as thr
                Graphics.process = thr.Thread(target=Graphics.server_entry)
            else:
                Graphics.process = mp.Process(target=Graphics.server_entry)
            Graphics.process.start()

    @staticmethod
    def enqueue(obj):
        if not Graphics.process:
            raise RuntimeError("Graphics is not initialized")
        Graphics.event_queue.put_nowait(obj)

    @staticmethod
    def server_entry():
        Graphics().run()

    @staticmethod
    def shutdown():
        Graphics.enqueue(None)
        if Graphics.process:
            Graphics.process.join()

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Graphics, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "initialized"):
            return
        self.initialized = True
        if not Graphics.process:
            raise RuntimeError("Graphics server must be launched before "
                               "the initialization")
        self.exiting = False
        self.showed = False
        self.root = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        import matplotlib
        import matplotlib.cm as cm
        import matplotlib.lines as lines
        import matplotlib.patches as patches
        import matplotlib.pyplot as pp
        pp.ion()
        self.matplotlib = matplotlib
        self.cm = cm
        self.lines = lines
        self.patches = patches
        self.pp = pp
        """Creates and runs main graphics window.
        Note that this function should be called only by __init__()
        """
        self.logger.info("Server is running in process %d", os.getpid())
        if pp.get_backend() == "TkAgg":
            import tkinter
            self.root = tkinter.Tk()
            self.root.withdraw()
            self.root.after(100, self.update)
            tkinter.mainloop()
        elif pp.get_backend() == "Qt4Agg":
            from PyQt4 import QtGui, QtCore
            self.root = QtGui.QApplication([])
            self.timer = QtCore.QTimer(self.root)
            self.timer.timeout.connect(self.update)
            self.timer.start(Graphics.interval * 1000)
            self.root.exec_()
        elif pp.get_backend() == "WebAgg":
            matplotlib.rcParams['webagg.port'] = config.webagg_port
            matplotlib.rcParams['webagg.open_in_browser'] = 'False'
            while not self.exiting:
                self.update()
                time.sleep(Graphics.interval)

    def update(self):
        """Processes all events scheduled for plotting
        """
        try:
            processed = set()
            while True:
                plotter = self.event_queue.get_nowait()
                if not plotter:
                    self.exiting = True
                    break
                if plotter in processed:
                    continue
                processed.add(plotter)
                plotter.redraw()
                if self.pp.get_backend() == "WebAgg" and not self.showed:
                    self.showed = True
                    self.pp.show()
        except queue.Empty:
            pass
        if self.pp.get_backend() == "TkAgg":
            if not self.exiting:
                self.root.after(Graphics.interval * 1000, self.update)
            else:
                self.logger.debug("Terminating the main loop")
                self.root.destroy()
        if self.pp.get_backend() == "Qt4Agg" and self.exiting:
            self.timer.stop()
            self.logger.debug("Terminating the main loop")
            self.root.quit()
