
import sqlalchemy
import common



class axis(object):
    def __init__(self, axis, name=None):
        self.axis = axis
        self.name = name

    def validate(self, cube):
        self.object = cube
        self.axis.validate(cube)

    def name_set(self, name):
        self.name = name

    def __repr__(self):
        res = '\t<olap.axis ['+str(self.name)+']\n'
        res += str(self.axis)
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
        result = self.axis.run(metadata)
        return result

# vim: ts=4 sts=4 sw=4 si et
