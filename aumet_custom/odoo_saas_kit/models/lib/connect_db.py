import os,time,sys,shutil
import random, string
import json
import subprocess
import imp,re,shutil
import argparse
import logging
import psycopg2


def isdbaccessible(details):
    try:
        psycopg2.connect(
                dbname="postgres",
                user=details['user'],
                password=details['password'],
                host=details['host'],
                port=details['port'])
        print("Yes")
    except Exception as e:
        print("Error while connecting DB :-%r"%e)

if __name__ == "__main__":
    isdbaccessible(details = { "user":sys.argv[1], "password" : sys.argv[2],
        "host": sys.argv[3], "port" : sys.argv[4]})
