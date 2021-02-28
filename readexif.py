#!/usr/bin/env python3
#-*-coding: utf-8 -*-
#pylint: disable=W0141

import os
import sys
import exifread
import hashlib
import string
import logging

fp = open(sys.argv[1], 'rb')
exif = exifread.process_file(fp)

fp.close()
#print exif

print(exif)
