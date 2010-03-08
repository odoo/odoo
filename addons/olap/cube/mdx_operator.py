import common

#
# Class constructed by {..., ...}
#
class mdx_set(object):
    def __init__(self, list):
        self.list = list

    def run(self, metadata):
        """
            Should use xcombine, I think it's currently False
            common.xcombine(*result)
        """
        result = []
        for l in self.list:
            result += l.run(metadata)
        position = 0
        for r in result:
            r['delta'] = position
            position += len(r['value'])
        return result

    def validate(self, object):
        for l in self.list:
            l.validate(object)
        return True

    def __repr__(self):
        res = '\tSet: ['
        for l in self.list:
            res += str(l)+',\n'
        res += '\t]'
        return res
# vim: ts=4 sts=4 sw=4 si et
