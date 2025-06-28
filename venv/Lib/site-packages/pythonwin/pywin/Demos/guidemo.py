# GUI Demo - just a worker script to invoke all the other demo/test scripts.
import sys

import __main__
import pywin.dialogs.list

demos = [
    ("Font", "import fontdemo;fontdemo.FontDemo()"),
    ("Open GL Demo", "import openGLDemo;openGLDemo.test()"),
    ("Threaded GUI", "import threadedgui;threadedgui.ThreadedDemo()"),
    ("Tree View Demo", "import hiertest;hiertest.demoboth()"),
    ("3-Way Splitter Window", "import splittst;splittst.demo()"),
    ("Custom Toolbars and Tooltips", "import toolbar;toolbar.test()"),
    ("Progress Bar", "import progressbar;progressbar.demo()"),
    ("Slider Control", "import sliderdemo;sliderdemo.demo()"),
    ("Dynamic window creation", "import createwin;createwin.demo()"),
    ("Various Dialog demos", "import dlgtest;dlgtest.demo()"),
    ("OCX Control Demo", "from ocx import ocxtest;ocxtest.demo()"),
    ("OCX Serial Port Demo", "from ocx import ocxserialtest; ocxserialtest.test()"),
    (
        "Internet Explorer Control Demo",
        'from ocx import webbrowser; webbrowser.Demo("https://www.python.org")',
    ),
]


def _exec_demo(cmd):
    try:
        exec(cmd)
    except Exception as error:
        print(f"Demo of {cmd} failed - {type(error)}:{error}")


def demo():
    if "/go" in sys.argv:
        for name, cmd in demos:
            _exec_demo(cmd)
        return

    # Otherwise allow the user to select the demo to run
    while True:
        rc = pywin.dialogs.list.SelectFromLists("Select a Demo", demos, ["Demo Title"])
        if rc is None:
            break
        title, cmd = demos[rc]
        _exec_demo(cmd)


if __name__ == __main__.__name__:
    import demoutils

    if demoutils.NeedGoodGUI():
        demo()
