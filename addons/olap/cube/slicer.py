
import sqlalchemy
import common

class slicer(object):
    def __init__(self, slicer):
        self.slicer = slicer

    def validate(self, cube):
        self.object = cube
        for slicer in self.slicer:
            slicer.validate(cube)

    def __repr__(self):
        res = '\t<olap.slicer\n'
        res += str(self.slicer)
        res += '\t>'
        return res

#
# Output:
#    a list of grouped values that can be computed at once
#    a group is defined by elements having the same query
#
#   [
#     {
#       'level': ["Time","2008","Q1"],
#       'value': '1er Trim 2008',
#       'query': SQLAlchemy query object
#     }
#   ]
#
    def run(self, metadata):
        print '*'*40
        print self.slicer
        result = []
        for slicer_line in self.slicer:
            res = slicer_line.run(metadata)
            result += slicer_line.run(metadata)
        return result

# vim: ts=4 sts=4 sw=4 si et
