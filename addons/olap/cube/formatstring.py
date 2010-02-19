class formatstring_class(object):
    def __init__(self):
        self.formatstrings = {}
    def subscribe(self, name, data):
        self.formatstrings[name] = data
formatstring = formatstring_class()

# vim: ts=4 sts=4 sw=4 si et
