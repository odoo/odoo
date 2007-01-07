#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/setup.py
__version__=''' $Id: setup.py 2511 2005-01-14 15:42:12Z rgbecker $ '''

import os, sys, distutils, glob
from distutils.core import setup, Extension

# from Zope - App.Common.package_home

def package_home(globals_dict):
    __name__=globals_dict['__name__']
    m=sys.modules[__name__]
    r=os.path.split(m.__path__[0])[0]
    return r

pjoin = os.path.join
abspath = os.path.abspath
isfile = os.path.isfile
isdir = os.path.isfile
dirname = os.path.dirname
package_path = pjoin(package_home(distutils.__dict__), 'site-packages', 'reportlab')

def get_version():
    #determine Version
    if __name__=='__main__':
        HERE=os.path.dirname(sys.argv[0])
    else:
        HERE=os.path.dirname(__file__)

    #first try source
    FN = pjoin(HERE,'__init__')
    try:
        for l in open(pjoin(FN+'.py'),'r').readlines():
            if l.startswith('Version'):
                exec l.strip()
                return Version
    except:
        pass

    #don't have source, try import
    import imp
    for desc in ('.pyc', 'rb', 2), ('.pyo', 'rb', 2):
        try:
            fn = FN+desc[0]
            f = open(fn,desc[1])
            m = imp.load_module('reportlab',f,fn,desc)
            return m.Version
        except:
            pass
    raise ValueError('Cannot determine ReportLab Version')

def getVersionFromCCode(fn):
    import re
    tag = re.search(r'^#define\s+VERSION\s+"([^"]*)"',open(fn,'r').read(),re.M)
    return tag and tag.group(1) or ''

def _rl_accel_dir_info(dir):
    import stat
    fn = pjoin(dir,'_rl_accel')
    return getVersionFromCCode(fn),os.stat(fn)[stat.ST_MTIME]

def _cmp_rl_accel_dirs(a,b):
    return cmp(_rl_accel_dir_info(b),__rl_accel_dir_info(a))

def _find_rl_accel():
    '''locate where the accelerator code lives'''
    _ = []
    for x in [
            './rl_addons/rl_accel',
            '../rl_addons/rl_accel',
            '../../rl_addons/rl_accel',
            './rl_accel',
            '../rl_accel',
            '../../rl_accel',
            './lib'] \
            + glob.glob('./rl_accel-*/rl_accel')\
            + glob.glob('../rl_accel-*/rl_accel') \
            + glob.glob('../../rl_accel-*/rl_accel') \
            :
        fn = pjoin(x,'_rl_accel.c')
        if isfile(pjoin(x,'_rl_accel.c')):
            _.append(x)
    if _:
        if len(_)>1: _.sort(_cmp_rl_accel_dirs)
        return abspath(_[0])
    return None

_FILES= [
        'README',
        'changes',
        'license.txt',

        'demos/colors/colortest.py',
        'demos/gadflypaper/00readme.txt',
        'demos/gadflypaper/gfe.py',
        'demos/odyssey/00readme.txt',
        'demos/odyssey/dodyssey.py',
        'demos/odyssey/fodyssey.py',
        'demos/odyssey/odyssey.py',
        'demos/odyssey/odyssey.txt',
        'demos/rlzope/readme.txt',
        'demos/rlzope/rlzope.py',
        'demos/stdfonts/00readme.txt',
        'demos/stdfonts/stdfonts.py',
        'demos/tests/testdemos.py',

        'docs/00readme.txt',
        'docs/genAll.py',
        'docs/graphguide/ch1_intro.py',
        'docs/graphguide/ch2_concepts.py',
        'docs/graphguide/ch3_shapes.py',
        'docs/graphguide/ch4_widgets.py',
        'docs/graphguide/ch5_charts.py',
        'docs/graphguide/gengraphguide.py',
        'docs/images/Edit_Prefs.gif',
        'docs/images/Python_21.gif',
        'docs/images/Python_21_HINT.gif',
        'docs/images/fileExchange.gif',
        'docs/images/jpn.gif',
        'docs/images/jpnchars.jpg',
        'docs/images/lj8100.jpg',
        'docs/images/replogo.a85',
        'docs/images/replogo.gif',
        'docs/reference/build.bat',
        'docs/reference/genreference.py',
        'docs/reference/reference.yml',
        'docs/userguide/app_demos.py',
        'docs/userguide/ch1_intro.py',
        'docs/userguide/ch2_graphics.py',
        'docs/userguide/ch2a_fonts.py',
        'docs/userguide/ch3_pdffeatures.py',
        'docs/userguide/ch4_platypus_concepts.py',
        'docs/userguide/ch5_paragraphs.py',
        'docs/userguide/ch6_tables.py',
        'docs/userguide/ch7_custom.py',
        'docs/userguide/ch9_future.py',
        'docs/userguide/genuserguide.py',
        'docs/userguide/testfile.txt',

        'extensions/README',
        
        'fonts/00readme.txt',
        'fonts/LeERC___.AFM',
        'fonts/LeERC___.PFB',
        'fonts/luxiserif.ttf',
        'fonts/luxiserif_license.txt',
        'fonts/rina.ttf',
        'fonts/rina_license.txt',

        'test/pythonpowered.gif',

        'tools/README',
        'tools/docco/README',
        'tools/py2pdf/README',
        'tools/py2pdf/demo-config.txt',
        'tools/py2pdf/vertpython.jpg',
        'tools/pythonpoint/README',
        'tools/pythonpoint/pythonpoint.dtd',
        'tools/pythonpoint/demos/htu.xml',
        'tools/pythonpoint/demos/LeERC___.AFM',
        'tools/pythonpoint/demos/LeERC___.PFB',
        'tools/pythonpoint/demos/leftlogo.a85',
        'tools/pythonpoint/demos/leftlogo.gif',
        'tools/pythonpoint/demos/lj8100.jpg',
        'tools/pythonpoint/demos/monterey.xml',
        'tools/pythonpoint/demos/outline.gif',
        'tools/pythonpoint/demos/pplogo.gif',
        'tools/pythonpoint/demos/python.gif',
        'tools/pythonpoint/demos/pythonpoint.xml',
        'tools/pythonpoint/demos/spectrum.png',
        'tools/pythonpoint/demos/vertpython.gif',
        ]
# why oh why don't most setup scripts have a script handler?
# if you don't have one, you can't edit in Pythonwin
def run():
    RL_ACCEL = _find_rl_accel()
    LIBS = []
    DATA_FILES = {}
    if not RL_ACCEL:
        EXT_MODULES = []
        print '***************************************************'
        print '*No rl_accel code found, you can obtain it at     *'
        print '*http://www.reportlab.org/downloads.html#_rl_accel*'
        print '***************************************************'
    else:
        fn = pjoin(RL_ACCEL,'lib','hyphen.mashed')
        if isfile(fn): DATA_FILES[pjoin(package_path, 'lib')] = [fn]
        EXT_MODULES = [
                    Extension( '_rl_accel',
                                [pjoin(RL_ACCEL,'_rl_accel.c')],
                                include_dirs=[],
                            define_macros=[],
                            library_dirs=[],
                            libraries=LIBS, # libraries to link against
                            ),
                    Extension( 'sgmlop',
                            [pjoin(RL_ACCEL,'sgmlop.c')],
                            include_dirs=[],
                            define_macros=[],
                            library_dirs=[],
                            libraries=LIBS, # libraries to link against
                            ),
                    Extension( 'pyHnj',
                            [pjoin(RL_ACCEL,'pyHnjmodule.c'),
                             pjoin(RL_ACCEL,'hyphen.c'),
                             pjoin(RL_ACCEL,'hnjalloc.c')],
                            include_dirs=[],
                            define_macros=[],
                            library_dirs=[],
                            libraries=LIBS, # libraries to link against
                            ),
                    ]
    for fn in _FILES:
        fn = os.sep.join(fn.split('/'))
        if isfile(fn):
            tn = dirname(fn)
            tn = tn and pjoin(package_path,tn) or package_path
            DATA_FILES.setdefault(tn,[]).append(fn)
    setup(
            name="Reportlab",
            version=get_version(),
            license="BSD license (see license.txt for details), Copyright (c) 2000-2003, ReportLab Inc.",
            description="The Reportlab Toolkit",
            long_description="""The ReportLab Toolkit.
An Open Source Python library for generating PDFs and graphics.
""",

            author="Robinson, Watters, Becker, Precedo and many more...",
            author_email="info@reportlab.com",
            url="http://www.reportlab.com/",

            package_dir = {'reportlab': '.'},

            packages=[ # include anything with an __init__
                    'reportlab',
                    'reportlab.extensions',
                    'reportlab.graphics.charts',
                    'reportlab.graphics.samples',
                    'reportlab.graphics.widgets',
                    'reportlab.graphics',
                    'reportlab.lib',
                    'reportlab.pdfbase',
                    'reportlab.pdfgen',
                    'reportlab.platypus',
                    'reportlab.test',
                    'reportlab.tools.docco',
                    'reportlab.tools.py2pdf',
                    'reportlab.tools.pythonpoint.styles',
                    'reportlab.tools.pythonpoint',
                    'reportlab.tools',
                     ],
            data_files = DATA_FILES.items(),
            ext_modules =   EXT_MODULES,
        )

if __name__=='__main__':
    run()
