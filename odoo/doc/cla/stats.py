#!/usr/bin/python
#
# Runme From the repo toplevel directory
#
from __future__ import print_function
import subprocess
import glob
import re
import pprint


cla_glob = "doc/cla/*/*.md"
cla = ''.join(open(f).read() for f in glob.glob(cla_glob))
cla = cla.lower()

def cla_signed(email):
    if re.match('.*(odoo|openerp|tinyerp).com$',email):
        return True
    if cla.find(email) != -1:
        return True
    return False

def blamestat(ext='py'):
    r = {}
    ok = 0
    okl = []
    ko = 0
    kol = []
    p = subprocess.Popen("git ls-tree -r -z --name-only HEAD | grep -z '.%s$' | xargs -0 -n1 git blame --line-porcelain HEAD |grep  '^author-mail ' |sort |uniq -c|sort -nr" % ext, shell=True, stdout = subprocess.PIPE)
    for i in p.stdout.read().split('\n'):
        mo = re.search(r'(\d+) author-mail <([^ @<]+@[^ @<]+)>',i)
        if mo:
            lines = int(mo.group(1))
            email = mo.group(2)
            if cla_signed(email):
                ok += lines
                okl.append(i)
            else:
                ko += lines
                kol.append(i)
    print('-'*60)
    print('Stats for ', ext)
    print('-'*60)
    print("\nCLA SIGNED %s/%s (%.0f%%)" % (ok, ok+ko, ok*100.0/(ok+ko)))
    for i in okl:
        print(i)

    print("\nCLA MISSING %s/%s (%.0f%%)\n" % (ko, ok+ko, ko*100.0/(ok+ko)))
    for i in kol:
        print(i)
    print()
    print()

blamestat('md')
blamestat('rst')
blamestat('py')
blamestat('js')
blamestat('xml')
blamestat('csv')
