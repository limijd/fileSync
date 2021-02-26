#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=C0103,W0703,R0902,R1711,R0912,R0914,R0911

import os
import sys
import re
import argparse
import logging
import scandir

class FileScan:
    def __init__(self, args=None):
        pass

    def scan(self, directory, all_files={}, file_types={}):
        logging.debug("Scan %s ...", directory)
        for entry in os.scandir(directory):
            if entry.is_file():
                ty = os.path.splitext(entry.name)[1]
                stat = entry.stat()
                if ty in file_types:
                    count, sz_count,files = file_types[ty]
                    sz_count = sz_count + stat.st_size
                    files.append(entry.path)
                    file_types[ty] = [count+1, sz_count, files]
                else:
                    file_types[ty] = [1, stat.st_size, [entry.path] ]
                all_files[entry.path] = [entry.name, entry.path, entry.stat(), entry.is_symlink()]
            elif entry.is_dir():
                self.scan(entry.path, all_files, file_types)

        return all_files, file_types

if __name__ == "__main__":
    fs = FileScan()
    all_files, file_types = fs.scan(sys.argv[1])
    for k,v in file_types.items():
        print(k,v)

