#!/usr/bin/python3 
#-*-coding: utf-8 -*-
#pylint: disable=W0141,W0614,W0401
import logging

DB_CONFIG={}

DB_CONFIG["TABLES"] = {}

DB_CONFIG["TABLES"]["TblFile"] = [
    {"fId":"INTEGER PRIMARY KEY "},
    {"st_size":"INTEGER"},
    {"st_atime":"INTEGER"},
    {"st_mtime":"INTEGER"},
    {"st_ctime":"INTEGER"},
    {"from_abs_path":"TEXT"},
    {"md5":"TEXT"},
    {"refined_fn":"TEXT"},
    {"ext":"TEXT"}
]


import os
import sys
import json
import datetime
from contextlib import closing
import sqlite3

"""
class MyDB

Note: 
1. establish connection and close the connection immediately after
each transaction is the default behavior.
"""
class MyDB:
    def __init__(self, config, sqlite_db, log=None):
        self.config = config
        self.sqlite_db = sqlite_db
        self.log = None
        self.conn = None
        self.err = []
        self.sql_count = 0

        self.log = log
        if log and log != sys.stdout:
            self.log = open(log, "w")
            assert(0)

    def Connect(self):
        logging.debug("Connect to database: %s", self.sqlite_db)
        assert(not self.conn)
        self.conn = sqlite3.connect(self.sqlite_db)
        assert(self.conn)
        return

    def Close(self, rollback=False):
        if not self.conn: 
            return

        if rollback:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()
        self.conn = None


    def RunSQL(self, sql, disconn=True, commit=True, fetchall=False):
        logging.debug("run sql: %s", sql)
        if not self.conn:
            self.Connect()

        self.sql_count = self.sql_count + 1
        results = None
        with closing(self.conn.cursor()) as cur:
            cur.execute(sql)
            if commit:
                self.conn.commit()
            if fetchall:
                columns = cur.description
                results = []
                for value in cur.fetchall():
                    tmp = {}
                    for (index,column) in enumerate(value):
                        tmp[columns[index][0]] = column
                    results .append(tmp)
                
        if disconn:
            self.Close()

        return results

    def CheckTables(self):
        logging.info("Checking tables ...")
        tables = self.config["TABLES"]
        for tblName,fieldsDef in tables.items():
            self.CheckTable(tblName, fieldsDef)
        self.Close()

        self.CheckAndExtendTables()
        return

    def CheckTable(self, tblName, fieldsDef):
        fieldsSql = self.genFieldsSql(fieldsDef)
        sql = "CREATE TABLE IF NOT EXISTS %s ( %s)"  \
            % (tblName, fieldsSql)
        self.RunSQL(sql, disconn=False, commit=True)

    def genFieldsSql(self, fieldsDef, needType=True):
        if needType:
            return  ", ".join(map(lambda x:"%s %s" \
                %(list(x.keys())[0], list(x.values())[0]), fieldsDef))
        else:
            return  ", ".join(map(lambda x:"%s" \
                %(list(x.keys())[0]), fieldsDef))

    def genSqlFilter(self, matchFldData):
        sqls = []
        for k,v in matchFldData.items():
            sql = "%s=%s"%(k,self.sqlVal(v))
            sqls.append(sql)

        return ' AND '.join(sqls)

    def Delete(self, tblName, matchFldData, disconn=True, commit=True):
        assert(isinstance(matchFldData, dict))
        sql = "DELETE FROM %s WHERE %s"%(tblName
            , self.genSqlFilter(matchFldData))

        self.RunSQL(sql, disconn=disconn, commit=False, fetchall=False)
        return


    def Update(self, tblName, fldsAndData, matchFldData, disconn=True, commit=True):
        assert(isinstance(fldsAndData, dict))
        assert(isinstance(matchFldData, dict))

        sqlSet = ", ".join(map(lambda x:"%s=%s" \
            %(x,self.sqlVal(fldsAndData[x])) , list(fldsAndData.keys())))
        sql = "UPDATE %s SET %s WHERE %s"%(tblName, sqlSet
            , self.genSqlFilter(matchFldData))
        self.RunSQL(sql, disconn=disconn, commit=commit)

    def sqlVal(self, v):
        if v is None:
            return "NULL"
        elif isinstance(v, float):
            return "%f"%v
        elif isinstance(v, int):
            return "%d"%v
        #elif isinstance(v, long):
        #    return "%d"%v
        #elif isinstance(v, unicode):
        #    return "'%s'"%v.encode("utf-8")
        else:
            return "'%s'"%v

    def Insert(self, tblName, fldsData, disconn=True, commit=True):
        assert(isinstance(fldsData, list))


        fieldsDef = self.config["TABLES"][tblName]

        if "INTEGER PRIMARY KEY" in list(fieldsDef[0].values())[0]:
            fieldsDef = fieldsDef[1:]

        if len(fieldsDef) != len(fldsData):
            print(fieldsDef)
            print(fldsData)
            raise MyError("插入数据个数同数据表定义不符")

        fldsDeclSql = self.genFieldsSql(fieldsDef, needType=False)
        valuesSql = []
        for v in fldsData:
            valuesSql.append(self.sqlVal(v))

        valuesSql = ", ".join(valuesSql)

        sql = "INSERT INTO %s ( %s ) VALUES ( %s )" % (tblName \
            , fldsDeclSql, valuesSql)

        self.RunSQL(sql, disconn=disconn, commit=commit)
        return

    def Search(self, tblName, fldKV, sortFld=None, disconn=True
            , limit=None):

        sql = "SELECT * FROM %s WHERE %s "
        if sortFld:
            sql = sql + " ORDER by %s DESC " % sortFld
        sql = sql%(tblName, self.genSqlFilter(fldKV))
        if limit:
            sql = sql + " LIMIT %d"%limit 

        results = self.RunSQL(sql, disconn=disconn, commit=False
            , fetchall=True)

        return results

    def LoadTable(self, tblName, disconn=True
            , limit=None):

        sql = "SELECT * FROM %s " % tblName
        results = self.RunSQL(sql, disconn=disconn, commit=False
            , fetchall=True)

        return results


    def CheckAndExtendTables(self):
        for tblName in self.config["TABLES"]:
            self.CheckAndExtendTable(tblName)
        return                

    def CheckAndExtendTable(self, tblName):
        fieldsDef = self.config["TABLES"][tblName]

        sql = "SELECT * FROM %s LIMIT 1" % tblName
        results = self.RunSQL(sql, fetchall=True)
        if not results:
            return

        newFields = []
        assert(len(results) == 1)
        for fld in fieldsDef:
            k = list(fld.keys())[0]
            if not k in list(results[0].keys()):
                sql = "ALTER TABLE %s ADD %s %s" % (tblName, k, list(fld.values()[0]))
                self.RunSQL(sql)

        return



