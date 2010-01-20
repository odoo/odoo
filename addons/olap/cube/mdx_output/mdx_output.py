#
# Modify the final result (axis, data), for instance, reordering of axes
#
import copy

def decimal_to_float(cube):
# Note FP: I think the decimal > float conversion should be done more
# in upstream
    if type(cube)==type([]) and len(cube):
        if type(cube[0])==type([]):
            for b in cube:
                decimal_to_float(b)
        else:
            for l in range(len(cube)):
                cube[l] = str(float(cube[l]))

def sort_apply(cube, axis_pos):
    cube2 = copy.copy(cube)
    for i in range(len(axis_pos)):
        cube[i] = cube2[axis_pos[i]]
    return cube

def sort_axis(data):
    for axis_id in range(len(data[0])):
        axis_pos = []
        for i in range(len(data[0][axis_id])):
            axis_pos.append((data[0][axis_id][i], i))
        axis_pos.sort()
        data[0][axis_id] = map(lambda x: x[0], axis_pos)
        axis_pos2 = map(lambda x: x[1], axis_pos)
        cubes = [ data[1] ]
        for i in range(axis_id):
            cubes2 = []
            for cube in cubes:
                cubes2 += cube
            cubes = cubes2
        for cube in cubes:
            sort_apply(cube, axis_pos2)

def mdx_output(data):
    print 'DATA',  data
#    decimal_to_float(data[1])
#    sort_axis(data) 
    return data

if __name__=='__main__':
	print 'Testing Code'
	data = ([[(['user'], 'All user')], [(['measures', 'credit_limit'], 'credit_limit'), (['measures', 'count'], 'count')]], [[[66700.0], [22L]]])
	data = ([[([u'Products'], u'All Products'), ([u'Order Date'], u'All Order Date')]], [[False], [False]])
	data = ([[([u'Order Date'], u'All Order Date'), ([u'Order Date', 2007.0], 2007.0), ([u'Order Date', 2008.0], 2008.0), ([u'Order Date', 2007.0, 'Q1'], 'Q1'), ([u'Order Date', 2007.0, 'Q2'], 'Q2'), ([u'Order Date', 2007.0, 'Q3'], 'Q3'), ([u'Order Date', 2007.0, 'Q4'], 'Q4'), ([u'Users'], u'All Users'), ([u'Users', 'Administrator'], 'Administrator'), ([u'Users', 'Demo User'], 'Demo User'), ([u'Users', 'Root'], 'Root'), ([u'Partner Country'], u'All Partner Country'), ([u'Partner Country', 'Belgium'], 'Belgium'), ([u'Partner Country', 'China'], 'China'), ([u'Partner Country', 'France'], 'France'), ([u'Partner Country', 'Taiwan'], 'Taiwan')]], [[False], [False], [False], [False], [False], [False], [False], [False], [False], [False], [False], [False], [False], [False], [False], [False]])
	data = ([[([u'Order Date'], u'All Order Date'), ([u'Order Date', 2007.0], 2007.0), ([u'Order Date', 2008.0], 2008.0), ([u'Order Date', 2007.0, 'Q1'], 'Q1'), ([u'Order Date', 2007.0, 'Q2'], 'Q2'), ([u'Order Date', 2007.0, 'Q3'], 'Q3'), ([u'Order Date', 2007.0, 'Q4'], 'Q4'), ([u'Users'], u'All Users'), ([u'Users', 'Administrator'], 'Administrator'), ([u'Users', 'Demo User'], 'Demo User'), ([u'Users', 'Root'], 'Root'), ([u'Partner Country'], u'All Partner Country'), ([u'Partner Country', 'Belgium'], 'Belgium'), ([u'Partner Country', 'China'], 'China'), ([u'Partner Country', 'France'], 'France'), ([u'Partner Country', 'Taiwan'], 'Taiwan')], [(['measures', u'Items Sold'], u'Items Sold')]], [[[Decimal("258.00")]], [[Decimal("34.00")]], [[Decimal("224.00")]], [[Decimal("12.00")]], [[Decimal("9.00")]], [[Decimal("6.00")]], [[Decimal("7.00")]], [[Decimal("258.00")]], [[Decimal("204.00")]], [[Decimal("16.00")]], [[Decimal("38.00")]], [[Decimal("258.00")]], [[Decimal("17.00")]], [[Decimal("78.00")]], [[Decimal("139.00")]], [[Decimal("2.00")]]])
	print 'Old', data
	sort_axis(data)
	print 'New', data

# vim: ts=4 sts=4 sw=4 si et
