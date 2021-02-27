#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=C0103,W0703,R0902,R1711,R0912,R0914,R0911

import os
import sys
import re
import argparse
import logging
import yaml
import hashlib
import datetime
import shutil
from texttable import Texttable
from FileScan import *
from DBConfig import *

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))

class FileSync:
    def __init__(self, args):
        self.args = args
        pass

    def do_report(self):
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
        return

    def do_export_file_list(self):
        fs = FileScan()
        all_files, file_types, all_fns = fs.scan(args.src_directory)
        fp = open(args.export_file_list, "w")
        for ty, ft in file_types.items():
            fp.write("%s File Type: %s %s\n" %("="*30, ty, "="*30))
            for fn in ft[2]:
                fp.write("%s\n"%fn);
            fp.write("\n")
        fp.close()
        return

    def do_diff_new(self):
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

    def load_yaml_rule(self):
        fn_yaml =  SCRIPT_PATH + "/rule.yaml"
        logging.info("Loading yaml rule: %s", fn_yaml)
        fp = open(fn_yaml, "r")
        self.rules = yaml.full_load(fp)
        fp.close()

        #build self.dbpath
        db = self.rules["db"]
        if not db.startswith("/"):
            db = self.args.dest_directory + "/" + db
        self.dbpath = os.path.abspath(db)

        #build self.ext_rules
        self.ext_rules = {}
        for k, v in self.rules.items():
            if not "ext" in v:
                continue
            for ext in v["ext"]:
                self.ext_rules[ext] = v

        logging.info("Database: %s", self.dbpath)
        return

    def parse_fn(self, fnpath, md5=None):
        logging.debug("Parsing %s ...", fnpath)
        fn_vars = {}

        fn = fnpath.split("/")[-1]
        fn_noext, ext = os.path.splitext(fn)
        fn_vars["FN_ORIGNAME"] = fn_noext

        res = re.search(r"20[0-9][0-9]-[0-9]{1,2}-[0-3][0-9]", fn, re.UNICODE)
        if res:
            y,m,d = res.group(0).split("-")
            fn_vars["FN_YEAR"] = y
            fn_vars["FN_MONTH"] = m
            fn_vars["FN_DAY"] = d
            orig_name = re.sub(r"20[0-9][0-9]-[0-9]{1,2}-[0-3][0-9][-_]?", "", fn_noext, re.UNICODE)
            fn_vars["FN_ORIGNAME"] = orig_name

        res = re.search(r"20[0-9][0-9]\.[0-9]{1,2}\.[0-3][0-9]", fn, re.UNICODE)
        if res:
            y,m,d = res.group(0).split(".")
            fn_vars["FN_YEAR"] = y
            fn_vars["FN_MONTH"] = m
            fn_vars["FN_DAY"] = d
            orig_name = re.sub(r"20[0-9][0-9].[0-9]{1,2}.[0-3][0-9][-_]?", "", fn_noext, re.UNICODE)
            fn_vars["FN_ORIGNAME"] = orig_name

        res = re.search(r"20[0-9][0-9][0-9][0-9][0-3][0-9]", fn, re.UNICODE)
        if res:
            s = res.group(0)
            fn_vars["FN_YEAR"] = s[0:4]
            fn_vars["FN_MONTH"] = s[4:6]
            fn_vars["FN_DAY"] = s[6:8]
            orig_name = re.sub(r"20[0-9][0-9][0-9][0-9][0-3][0-9][-_]?", "", fn_noext, re.UNICODE)
            fn_vars["FN_ORIGNAME"] = orig_name

        stat = self.all_files_src[fnpath][2]
        mt = stat.st_mtime
        ct = stat.st_ctime
        dt = min(mt, ct)
        dt = datetime.datetime.fromtimestamp(dt)
        dts = dt.strftime("%Y.%m.%d").split(".")
        fn_vars["ST_MTIME_YEAR"] = dts[0]
        fn_vars["ST_MTIME_MONTH"] = dts[1]
        fn_vars["ST_MTIME_DAY"] = dts[2]
        fn_vars["ext"] = ext.strip(".")
        fn_vars["MD5_6"] = md5[0:6]

        return fn_vars

    def get_newfn(self, fnpath, fn_vars, rename_rules, goto_rules):
        fn = fnpath.split("/")[-1]
        VARS = ["FN_YEAR", "FN_MONTH", "FN_DAY", "ST_MTIME_YEAR", "ST_MTIME_MONTH",
                "ST_MTIME_DAY", "EXIF_YEAR", "EXIF_MONTH", "EXIF_DAY", "MP3_TITLE",
                "MP3_ALBUM", "FN_ORIGNAME", "ext", "MD5_6"]

        #rename 
        match_rule = None
        for rule in rename_rules:
            match_rule = rule 
            for v in VARS:
                k = "$%s"%v
                if rule.find(k)>=0:
                    if not v in fn_vars:
                        match_rule = None
            if match_rule:
                break

        if match_rule:
            newfn = match_rule
            for v in VARS:
                k = "$%s"%v
                if newfn.find(k)>=0:
                    s_from = "\$%s"%v
                    s_to = fn_vars[v]
                    newfn = re.sub(s_from, s_to, newfn, re.UNICODE)
        else:
            newfn = fn

        #go to directory
        match_rule = None
        for rule in goto_rules:
            match_rule = rule 
            for v in VARS:
                k = "$%s"%v
                if rule.find(k)>=0:
                    if not v in fn_vars:
                        match_rule = None
            if match_rule:
                break

        assert match_rule and "Cant identify target directory!"

        if match_rule:
            target_dir = match_rule
            for v in VARS:
                k = "$%s"%v
                if target_dir.find(k)>=0:
                    s_from = "\$%s"%v
                    s_to = fn_vars[v]
                    target_dir = re.sub(s_from, s_to, target_dir, re.UNICODE)
                
        target_dir = self.args.dest_directory + "/" + target_dir
        target_dir = os.path.abspath(target_dir)
        logging.info("%s -> %s/%s", fn, target_dir, newfn)
        return target_dir, newfn


    def sync_one_file(self, fnpath):
        fp = open(fnpath, "rb")
        fp.seek(0,0) #to beginning
        content = fp.read()
        fp.close()
        md5 = hashlib.md5(content).hexdigest()
        finfo = self.all_files_src[fnpath]
        finfo[4] = md5

        #check if file exists in DB
        try:
            exist = self.mydb.Search("TblFile",
                {
                    "st_size":finfo[2].st_size,
                    "st_mtime":finfo[2].st_mtime,
                    "st_ctime":finfo[2].st_ctime,
                    "from_abs_path":os.path.abspath(fnpath),
                    "md5":md5,
                }, disconn=False)
        except Exception as e:
            print(e)
            self.mydb.Close(rollback=False)
            sys.exit(6)

        if exist:
            logging.debug("%s exists in database already. skipped sync.")
            return

        ext = os.path.splitext(fnpath)[1]
        ext_rule = self.ext_rules[ext]

        fn_vars = self.parse_fn(fnpath, md5)
        target_dir, newfn = self.get_newfn(fnpath, fn_vars, ext_rule["rename"], ext_rule["goto"])

        if not os.path.exists(target_dir):
            logging.info("making dir: %s", target_dir)
            os.makedirs(target_dir)

        copy_successful = False
        try:
            shutil.copy2(fnpath, "%s/%s"%(target_dir, newfn))
            copy_successful = True
        except Exception as e:
            print(e)
            copy_successful = False
            logging.error("Error while copying file: %s -> %s/%s", fnpath, target_dir, newfn)

        if copy_successful:
            try:
                self.mydb.Insert("TblFile", 
                        [finfo[2].st_size, finfo[2].st_atime
                        , finfo[2].st_mtime
                        , finfo[2].st_ctime
                        , os.path.abspath(fnpath)
                        , md5
                        , newfn
                        , ext]
                    , disconn=True, commit=True)
                logging.debug("register %s to database", fnpath)
            except Exception as e:
                print(e)
                self.mydb.Close(rollback=False)
                sys.exit(7)

        return

    def sync_files(self, sync_queue):
        logging.info("%d files need to be synced", len(sync_queue))
        for fn in sync_queue:
            self.sync_one_file(fn)
        return

    def load_database_to_mem(self):
        logging.info("Loading TblFile from database to memory")
        self.TblFile = self.mydb.LoadTable("TblFile")
        return

    def do_sync_new(self):
        self.load_yaml_rule()
        self.mydb = MyDB(DB_CONFIG, self.dbpath)
        self.mydb.CheckTables()

        fs = FileScan()
        self.all_files_src, self.file_types_src, self.all_fns_src = fs.scan(self.args.src_directory)
        self.sync_queue = []
        for fn, finfo in self.all_files_src.items():
            ty = os.path.splitext(fn)[1]
            if not ty in self.ext_rules:
                continue
            self.sync_queue.append(fn)

        self.load_database_to_mem()
        self.sync_files(self.sync_queue)

        self.mydb.Close()
        return

