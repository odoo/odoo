#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/__init__.py
__version__=''' $Id: __init__.py 2877 2006-05-18 15:11:23Z andy $ '''
__doc__="""The Reportlab PDF generation library."""
Version = "2.0"

import sys

if sys.version_info[0:2] < (2, 3):
    warning = """The trunk of reportlab requires Python 2.3 or higher.
    Any older applications should either use released versions beginning
    with 1.x (e.g. 1.21), or snapshots or checkouts from our 'version1'
    branch.
    """
    raise ImportError("reportlab needs Python 2.3 or higher", warning)

def getStory(context):
    if context.target == 'UserGuide':
        # parse some local file
        import os
        myDir = os.path.split(__file__)[0]
        import yaml
        return yaml.parseFile(myDir + os.sep + 'mydocs.yaml')
    else:
        # this signals that it should revert to default processing
        return None


def getMonitor():
    import reportlab.monitor
    mon = reportlab.monitor.ReportLabToolkitMonitor()
    return mon
