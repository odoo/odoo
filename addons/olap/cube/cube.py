
import sqlalchemy
import common

class cube(object):
    def __init__(self, name=None):
        super(cube, self).__init__()
        self.object = False
        self.name = name

    def run(self, metadata):
        table = common.table_get(metadata, self.object.table_id)
        return sqlalchemy.select(from_obj = [table], columns=[]),table

    def validate(self, schema):
        for cube in schema.cube_ids:
            if self.name == cube.name:
                self.object = cube
                break
        return self.object

    def __repr__(self):
        return self.name
# vim: ts=4 sts=4 sw=4 si et
