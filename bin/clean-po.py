# -*- coding: utf-8 -*-
import sys
sys.path.append("tools")

import config
import tools

# Parses a po file and builds a mapping source -> transaltion.
# Calls skip(), msgid(), and mgstr() methods for each skipped line,
# source string and translation string.
class Translations(object):

    def skip(self, l):
        pass

    def msgid(self, l):
        pass

    def msgstr(self, l):
        pass

    translations = {}

    def __init__(self, filename):
        f = file(filename)
        while self.parse_file(f):
            pass
        f.close()

    def parse_file(self, f):
        source = ''
        trans = ''

        # Skips lines until a msgid is given then read the source string.
        line = f.readline()
        while not line.startswith('msgid'):
            if line.startswith('msgstr'):
                raise Exception('unexpected msgstr')
            if not line:
                return False
            self.skip(line.strip())
            line = f.readline()
        source = tools.unquote(line.strip()[6:])

        # Complete the source string.
        line = f.readline().strip()
        while not line.startswith('msgstr'):
            if not line:
                raise Exception('unexpected empty line')
            source += tools.unquote(line)
            line = f.readline().strip()
        self.msgid(source)

        # Read the translation.
        trans = tools.unquote(line[7:])
        line = f.readline().strip()
        while line:
            trans += tools.unquote(line)
            line = f.readline().strip()
        self.msgstr(trans)
        self.skip(line)

        self.translations[source] = trans
        return True

# Redefines skip(), msgid(), and msgstr() to replicate the input po file.
class CatTranslations(Translations):

    def skip(self, l):
        print l

    def msgid(self, l):
        print "msgid %s" % (tools.quote(l),)
        self.source = l

    def msgstr(self, l):
        if not self.source:
            print 'msgstr ""'
            print tools.quote(l)[0:-3]
        else:
            print "msgstr %s" % (tools.quote(l),)

# Redefines skip(), msgid(), and msgstr() to replicate the input po file but
# removing translations found in a given mapping.
class CleanTranslations(Translations):

    def __init__(self, filename, mapping):
        self.mapping = mapping
        super(CleanTranslations, self).__init__(filename)

    def skip(self, l):
        print l

    def msgid(self, l):
        print "msgid %s" % (tools.quote(l),)
        self.source = l

    def msgstr(self, l):
        if not self.source:
            print 'msgstr ""'
            print tools.quote(l)[0:-3]
        elif self.mapping.get(self.source) == l:
            print 'msgstr ""'
        else:
            print "msgstr %s" % (tools.quote(l),)

# Redefines skip(), msgid(), and msgstr() to spot the differences in
# translations between two po.
class DiffTranslations(Translations):

    def __init__(self, filename, mapping):
        self.mapping = mapping
        super(DiffTranslations, self).__init__(filename)

    def skip(self, l):
        pass

    def msgid(self, l):
        self.source = l

    def msgstr(self, l):
        if not self.source:
            pass
        elif self.mapping.get(self.source) != l:
            print "> %s" % self.mapping.get(self.source)
            print "< %s" % l

import os, fnmatch

# Finds xx_XX.po files with associated xx.po file, and
# returns them together with their (common) path.
def locate_po(root=os.curdir):
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, "*_*.po"):
            xx = filename.split('_')[0]
            xx_po = xx + ".po"
            if os.path.exists(os.path.join(path, xx_po)):
                yield (path, xx_po, filename)

def main():
    if not (len(sys.argv) in (2, 3, 4)):
        print "usages: python clean-po.py xx.po xx_XX.po"
        print "        python clean-po.py diff a.po b.po"
        print "        python clean-po.py path"
        exit(1)

    if len(sys.argv) == 2:
        for path, xx_po, xx_XX_po in locate_po(sys.argv[1]):
            print "%s\t%s\t%s" % (path, xx_po, xx_XX_po)

    if len(sys.argv) == 3:
        xx_po = sys.argv[1]
        xx_XX_po = sys.argv[2]

        m = Translations(xx_po)
        CleanTranslations(xx_XX_po, m.translations)

    elif len(sys.argv) == 4:
        a_po = sys.argv[2]
        b_po = sys.argv[3]

        m = Translations(a_po)
        DiffTranslations(b_po, m.translations)

#    CatTranslations("en_US.po")
#    CatTranslations("de.po")

if __name__ == "__main__":
    main()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
