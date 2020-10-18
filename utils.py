import logging
import os
import re

logging.basicConfig(level=logging.INFO)


class Utils:
    stop_words = ['i', 'am', 'we', 'are', 'he', 'she', 'is', 'they', 'was', 'where', 'do', 'does', 'did', 'done', 'has',
                  'have', 'had', 'be', 'been']

    @staticmethod
    def regex_checker(string, reg):
        prog = re.compile(reg)
        return prog.match(string)
