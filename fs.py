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

def cli(args):
    if args.report:
        fs = FileScan()
        all_files, file_types, all_fns = fs.scan(args.src_directory)
        tys = list(file_types.keys())
        tys.sort(key=lambda x:file_types[x][1], reverse=True)

        total_num_files = 0
        total_size = 0
        table = [["Type", "Total Size(MB)", "Num Files"]]
        for ty in tys:
            ft = file_types[ty]
            table.append([ty, ft[1]/1024/1024, ft[0]])
            total_num_files = total_num_files + ft[0]
            total_size = total_size + ft[1]

        text_table = Texttable()
        text_table.set_cols_dtype(['t', 'i', 'i'])
        text_table.add_rows(table)
        print(text_table.draw())

        print("Total Size:  %d"%total_size)
        print("Total Files: %d"%total_num_files)

    if args.export_file_list:
        fs = FileScan()
        all_files, file_types, all_fns = fs.scan(args.src_directory)
        fp = open(args.export_file_list, "w")
        for ty, ft in file_types.items():
            fp.write("%s File Type: %s %s\n" %("="*30, ty, "="*30))
            for fn in ft[2]:
                fp.write("%s\n"%fn);
            fp.write("\n")
        fp.close()


    if args.report_new_quick:
        assert args.src_directory
        assert args.dest_directory
        fs = FileScan()
        all_files_src, file_types_src, all_fns_src = fs.scan(args.src_directory)
        all_files_dest, file_types_dest, all_fns_dst = fs.scan(args.dest_directory)

        new_fns = []
        for fn, flist in all_fns_src.items():
            if fn in all_fns_dst:
                for x in flist:
                    f_src = all_files_src[x]
                    found = False
                    for y in all_fns_dst[fn]:
                        f_dst = all_files_dest[y]
                        if f_dst[2].st_size == f_src[2].st_size:
                            found = True
                    if not found:
                        new_fns.append(x)
            else:
                new_fns.extend(flist)

        for fn in new_fns:
            print(fn)
    return

def main():
    """ entry of program """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog=os.path.basename(__file__)
    , description="FileSync: File Sync")
    parser.add_argument('-d', '--debug', action='store_true', help="debug mode")
    parser.add_argument('-sd', '--src_directory', help='source directory')
    parser.add_argument('-dd', '--dest_directory', help='dest directory')
    parser.add_argument('-r', '--report', action='store_true', help='report source directory')
    parser.add_argument('-rnq', '--report_new_quick', action='store_true', help='report files that in source but not in dest ')
    parser.add_argument('-efl', '--export_file_list', help='report source directory')
    parser.set_defaults(func=cli)

    args = parser.parse_args()
    try:
        args.func
    except AttributeError:
        parser.error("too few arguments")

    if args.debug:
        logging.basicConfig(format='[alc: %(asctime)s %(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
    else:
        logging.basicConfig(format='[alc: %(asctime)s %(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

    args.func(args)

if __name__ == "__main__":
    main()
