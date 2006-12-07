#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/__init__.py
__version__=''' $Id$ '''
__doc__="""The Reportlab PDF generation library."""
Version = "1.20"

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
