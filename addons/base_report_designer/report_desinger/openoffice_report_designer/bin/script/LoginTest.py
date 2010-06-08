
if __name__<>"package":
    from ServerParameter import *
    from lib.gui import *

class LoginTest:
    def __init__(self):
        if not loginstatus:
            ServerParameter(None)

