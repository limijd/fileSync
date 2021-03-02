#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=C0103,W0703,R0902,R1711,R0912,R0914,R0911

import os
import sys
import re
import argparse
import logging
from texttable import Texttable

from FileScan import *
from DBConfig import *
from FileSync import *

def cli(args):
    fs = FileSync(args)
    if args.report:
        fs.do_report()

    if args.export_file_list:
        fs.do_export_file_list()

    if args.diff_new:
        fs.do_diff_new()

    if args.sync_new:
        fs.do_sync_new()

    return

def main():
    """ entry of program """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog=os.path.basename(__file__)
    , description="FileSync: File Sync")
    parser.add_argument('-d', '--debug', action='store_true', help="debug mode")
    parser.add_argument('-sd', '--src_directory', help='source directory')
    parser.add_argument('-dd', '--dest_directory', help='dest directory')
    parser.add_argument('-r', '--report', action='store_true', help='report source directory')
    parser.add_argument('-dn', '--diff_new', action='store_true', help='report files that in source but not in dest ')
    parser.add_argument('-sn', '--sync_new', action='store_true', help='sync files that in source but not in dest ')
    parser.add_argument('-rd', '--report_dup', action='store_true', help='report duplicated files in source directory')
    parser.add_argument('-efl', '--export_file_list', help='report source directory')
    parser.set_defaults(func=cli)

    args = parser.parse_args()
    try:
        args.func
    except AttributeError:
        parser.error("too few arguments")

    if args.debug:
        logging.basicConfig(format='[FileSync: %(asctime)s %(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
    else:
        logging.basicConfig(format='[FileSync: %(asctime)s %(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

    logging.getLogger("exifread").setLevel(logging.ERROR)

    args.func(args)

if __name__ == "__main__":
    main()
