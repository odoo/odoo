#!/usr/bin/env python

import gevent.monkey
gevent.monkey.patch_all()
import psycogreen.gevent
psycogreen.gevent.patch_psycopg()

import openerp

if __name__ == "__main__":
    openerp.cli.main()
