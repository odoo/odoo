
import sqlalchemy
import common
import level

class cross(object):
    def __init__(self, cross):
    	self.cross = cross
        self.name = False 
        self.object = False
        
    def validate(self, cube):
        for obj in self.cross:
            self.object = obj.validate(cube)
        return self.object
    
    def name_set(self, name):
        self.name = name
        
    def __repr__(self):
        res = '\t<olap.cross\n'
        res += str(self.cross)
        res += '\t>'
        return res
        
    def run(self, metadata):
        print '*'*40
        for obj in self.cross:
            result = obj.run(metadata)
        return result

# vim: ts=4 sts=4 sw=4 si et
