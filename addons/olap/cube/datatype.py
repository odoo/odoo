
class datatype_class(object):
    def __init__(self):
        self.datatype = {}
    def subscribe(self, name, data):
        self.datatype[name] = data
datatype = datatype_class()
# vim: ts=4 sts=4 sw=4 si et
