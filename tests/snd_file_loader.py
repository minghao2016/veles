"""
Created on May 21, 2013

@author: Markovtsev Vadim <v.markovtsev@samsung.com>
"""


import logging
import unittest
from snd_file_loader import SndFileLoader


class Test(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)

    def tearDown(self):
        pass

    def testSndFileLoader(self):
        loader = SndFileLoader()
        data = loader.decode_file(
            "/home/markhor/Development/speech_files/sawyer.flac")
        logging.info("%d samples at %d Hz" % (data["data"].size,
                                              data["sampling_rate"]))


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testSndFileLoader']
    unittest.main()
