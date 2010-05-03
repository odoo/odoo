import locale


import mdx_input
import sqlalchemy
import common
import slicer
import datetime
import pooler
import copy

class mapper(object):
    def __init__(self, size):
        self.size = size

class query(object):
    def __init__(self, axis, cube, slicer_obj=None, *args):
        super(query, self).__init__()
        self.object = False
        self.cube = cube
        self.axis = axis
        if not slicer_obj:
            slicer_obj = slicer.slicer([])
        self.slicer = slicer_obj

    #
    # Generate the cube with 'False' values
    # This function could be improved
    #
    def _cube_create(self, cube_size):
        cube_data = [False]
        while cube_size:
            newcube = []
            for i in range(cube_size.pop()):
                newcube.append(copy.deepcopy(cube_data))
            cube_data = newcube
        return cube_data

    def run(self,currency):
        db = sqlalchemy.create_engine(self.object.schema_id.database_id.connection_url,encoding='utf-8')
        metadata = sqlalchemy.MetaData(db)
        print 'Connected to database...', self.object.schema_id.database_id.connection_url
        #
        # Compute axis
        #
        axis = []
        axis_result = []
        cube_size = []
        cross = False
        cross_all = []
        for ax in self.axis:
            if ax.name == 'cross':
                cross = True
                cross = ax.run(metadata)
                cube_size[-1] = cube_size[-1] * len(cross)
                temp = axis_result[0][:] 
                cross_all.append(cross)
                final_axis = []
                for cr in cross:
                    for el in axis_result[-1]:
                        t = copy.deepcopy(el)
                        t = list(t)
                        t[0].append(cr['value'][0][0])
                        t.append(cr['value'][0][1])
                        final_axis.append(tuple(t))
                axis_result[-1]=final_axis[:]
                final_axis=[]
                len_axis = len(axis[-1])
                len_cross = len(cross)
                delta_count = 0 
                d=0  
                for data in common.xcombine(axis[-1],cross):
                    flag = False
                    make_where = []
                    temp_where = []
                    temp_column = []
                    if 'whereclause' in data[0]['query'].keys():
                        flag = True
                        temp_where = data[0]['query']['whereclause'][0] 
                        data[0]['query']['whereclause']=str(data[0]['query']['whereclause'][0])
                        
                    if isinstance(type(data[0]['query']['column'][0]),type(sqlalchemy.sql.expression._BindParamClause)):
                        temp_column = data[0]['query']['column'][0]
                        data[0]['query']['column'][0] = str(data[0]['query']['column'][0])
                    data_temp = copy.deepcopy(data[0])
                    if 'whereclause' in data[1]['query'].keys():
                        if 'whereclause' in data_temp['query'].keys():
                            make_where.append(data[1]['query']['whereclause'][0])
                        else:
                            make_where.append(data[1]['query']['whereclause'][0])
                    delta_count = delta_count + 1
                    if delta_count >= len_cross and len_cross!=1:
                        delta_count = 0 
                        data_temp['delta'] = d
                        d = d + 1
                    else:
                        data_temp['delta'] = d
                        d = d + 1
                    if flag:
                        data[0]['query']['whereclause']=[temp_where]
                        data_temp['query']['whereclause'] = [temp_where]
                    if make_where:
                        if 'whereclause' in data_temp['query'].keys():
                            data_temp['query']['whereclause'].append(make_where[0])
                        else:
                            data_temp['query']['whereclause'] = make_where
                    if temp_column:
                        data[0]['query']['column'] = [temp_column]
                        data_temp['query']['column'] = [temp_column]
                    final_axis.append(data_temp)
                axis[-1] = []
                axis[-1] = final_axis
            else:
                cross = False
                result = ax.run(metadata)
                length = 0
                axis_result2 = []
                for r in result:
                    length += len(r['value'])
                    axis_result2 += map(lambda x: (map(lambda y: y or False,x[0]),x[1] or False), r['value'])
                axis_result.append(axis_result2)
                axis.append(result)
                cube_size.append(length)    
        cube_data = self._cube_create(cube_size)
        cr = []
        slice = self.slicer.run(metadata)
        position = 0
        ax = []
        for subset in common.xcombine(*axis):
            select,table_fact = self.cube.run(metadata)
            for s in subset+slice:
                for key,val in s['query'].items():
                    for v in val:
                        if key=='column':
                            v = v.label('p_%d' % (position,))
                            position += 1
                            select.append_column(v)
                        elif key=='whereclause':
                            select.append_whereclause(v)
                        elif key=='group_by':
                            select.append_group_by(v)
                        else:
                            raise 'Error, %s not implemented !'% (key,)
#            metadata.bind.echo = True
            query = select.execute()
            result = query.fetchall()
            for record in result:
                cube = cube_data
                r = list(record)
                value = False
                for s in subset:
                    if s.has_key('format'):
                        # To make use of the format string if specified for the measure
                        # Its set to static for a testing
                        if not currency:
                            currency = "EUR"
                        if isinstance(r[0],float) or isinstance(r[0],int) or isinstance(r[0],long):
                            a = {'data':r[0]}
                            r[0] = str(r[0])
                        else:
                            r[0] = '0.0'
                            a = {'data':0.0}
                        if s['format'] == 'cr_prefix':
                            r[0] = currency + " "  + "%.2f"%a['data']
                        elif s['format'] == 'cr_postfix':
                            r[0] = "%.2f"%a['data'] + " " + currency
                        elif s['format'] == 'comma_sep':
                            r[0] = locale.format("%(data).2f", a, 1)
                        elif s['format'] == 'cr_prefix_comma':
                            r[0] = locale.format("%(data).2f", a, 1)
                            r[0] = currency + " "  + str(r[0])
                        elif s['format'] == 'cr_postfix_comma':
                            a['currency'] = currency
                            r[0] = locale.format("%(data).2f %(currency)s", a, 1)
                    cube = s['axis_mapping'].cube_set(cube, r, s['delta'])
                    value = s['axis_mapping'].value_set(r) or value
                for s in slice:
                    value = s['axis_mapping'].value_set(r) or value
                if value:
                    assert not cube[0], 'Already a value in cube, this is a bug !'
                    cube[0] = value

        i=0
        for a in cube_data:
            i=i+1;
        return (axis_result, cube_data)

    def preprocess(self):
        wrapper = mdx_input.mdx_input()
        wrapper.parse(self)

    def validate(self, schema):
        """ This function takes a query object and validate and assign
        fact data to it. Browse object from Tiny ERP"""
        cube = self.cube.validate(schema)
        self.object = cube
        if not self.object:
            raise "Cube '%s' not found in the schema '%s' !"%(cube.name, schema.name)
        self.slicer.validate(cube)

        for axis in self.axis:
            axis.validate(cube)
        for dimension in cube.dimension_ids:
            pass
        return True,cube

    def __repr__(self):
        res = '<olap.query ['+str(self.cube)+']\n'
        for l in self.axis:
            res+= '\tAxis: '+str(l)+'\n'
        res+= '\tSlicer:\n'+str(self.slicer)+'\n'
        res += '>'
        return res

    def log(self,cr,uid,cube,query,context={}):
        if not context==False:
            log_ids = pooler.get_pool(cr.dbname).get('olap.query.logs').search( cr, uid, [('query','=', query), ('user_id','=', uid)])
            if log_ids:
                count = pooler.get_pool(cr.dbname).get('olap.query.logs').browse(cr, uid, log_ids, context)[0]
                pooler.get_pool(cr.dbname).get('olap.query.logs').write(cr, uid, log_ids, {'count':count.count+1})
                
            else:
                logentry={}
                logentry['user_id']=uid
                logentry['cube_id']=cube.id
                logentry['query']=query
                logentry['time']= str(datetime.datetime.now())
                logentry['result_size']=0
                logentry['count']=1
                logentry['schema_id'] = cube.schema_id.id
                log_id = pooler.get_pool(cr.dbname).get('olap.query.logs').create(cr,uid,logentry)
#                count = pooler.get_pool(cr.dbname).get('olap.query.logs').browse(cr, uid, log_id, context)
#                pooler.get_pool(cr.dbname).get('olap.query.logs').write(cr, uid, log_id, {'count':count.count+1})
                return log_id
        return -1
# vim: ts=4 sts=4 sw=4 si et
