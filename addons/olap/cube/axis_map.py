#
# Interface for all mapping objects to map values into the right
# position in the cube, according to cube definition
#

class mapping(object):
    def query_init(self):
        pass
    def position_get(self):
        return 0

class column_static(mapping):
    def __init__(self, value=False, position=0):
        self.value = value
    def cube_set(self, cube, value, delta=0):
        return cube[ delta]
    def value_set(self, value=False):
        value.pop(0)
        return self.value


class column_static_dummy(mapping):
    def __init__(self, value=False, position=0):
        self.value = value
    def cube_set(self, cube, value, delta=0):
        return cube[ delta]
    def value_set(self, value=False):
        value.pop(0)
        return self.value

class column_fixed(mapping):
    def __init__(self, pos=0, position=0):
        self.pos = pos
    def cube_set(self, cube, value, delta=0):
        return cube[ self.pos +delta]
    def value_set(self, value):
        return value.pop(0)

class column_mapping_value(mapping):
    def __init__(self, value, position=0):
        self.axis_value = {}
        for v in range(len(value)):
            self.axis_value[value[v][0]] = v

    def cube_set(self, cube, value, delta=0):
        pos = value.pop(0)
        return cube[ self.axis_value[pos]+delta ]
    def value_set(self, value):
        return False

class column_mapping(mapping):
    def __init__(self, value, position=0):
        self.axis_value = {}
        for v in range(len(value)):
            self.axis_value[value[v][0]] = v

    def cube_set(self, cube, value, delta=0):
        pos = value.pop(0)
        return cube[ self.axis_value[pos]+delta ]

    def value_set(self, value):
        return False

    def position_get(self):
        return 1


class column_mapping_axis(mapping):
    def __init__(self, mapping, axis, position=0):
        keys = {}
        i = 0
        for a in axis:
            keys[tuple(list(a)[0][1:])] = i
            i+=1

        self.axis_value = {}
        for m in mapping:
            k = tuple(list(m)[:-1])
            a = keys[k]
            self.axis_value[tuple(m)[-1]] = a

    def cube_set(self, cube, value, delta=0):
        pos = value.pop(0)
        return cube[ self.axis_value[pos]+delta ]

    def value_set(self, value):
        return False

    def position_get(self):
        return 1



class column_mapping_join(mapping):
    def __init__(self, mappings, position=0):
        self.mappings = mappings

    def cube_set(self, cube, value, delta=0):
        for m in self.mappings:
            cube = m.cube_set(cube, value, delta)
        return cube

    def value_set(self, value):
        for m in self.mappings:
            value = m.value_set(value)
        return value


# vim: ts=4 sts=4 sw=4 si et
