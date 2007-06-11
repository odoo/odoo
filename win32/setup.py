# setup.py
from distutils.core import setup
import py2exe


setup(service=["TinyERPServerService"],
      options={"py2exe":{"excludes":["Tkconstants","Tkinter","tcl",
                                     "_imagingtk","PIL._imagingtk",
                                     "ImageTk", "PIL.ImageTk",
                                     "FixTk"],
                         "compressed": 1}}
      )
