
class level_interface(object):
    #
    # Return the number of position consummed by this level
    # 1 means this goes to the next level object (.[20])
    # 0 means that the next argument is still on the same level object (.children)
    #
    def validate(self, level, name):
        return 1

    def run(self, level, metadata, table):
        col = None
        return {}
# vim: ts=4 sts=4 sw=4 si et
