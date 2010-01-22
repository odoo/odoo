
import sqlalchemy
import common
import axis_map
import pooler,tools

class level(object):
    def __init__(self, level, sublevels=[]):
        self.level = level
        self.sublevels = sublevels
        self.object = False

    def validate(self, cube):
        for dimension in cube.dimension_ids:
            if self.object:
                break
            for hierarchy in dimension.hierarchy_ids:
                if hierarchy.name==self.level:
                    self.object = hierarchy
                    break

        #
        # TODO: implement access to unique levels for not fully qualified names
        #
        if not self.object:
            raise 'This dimension (%s) does not exist !' % (self.level,)

        obj = hierarchy
        pos = 0
        for level in self.sublevels:
            res = level.validate(hierarchy.level_ids[pos])
            if res:
                pos += 1
        return self.object

    def _to_unicode(self,s):
        try:
            return s.encode('ascii')
        except UnicodeError:
            try:
                return s.decode('utf-8')
            except UnicodeError:
                try:
                    return s.decode('latin')
                except UnicodeError:
                    return s

    def _to_decode(self,s):
        try:
            return s.encode('utf-8')
        except UnicodeError:
            try:
                return s.encode('latin')
            except UnicodeError:
                try:
                    return s.decode('ascii')
                except UnicodeError:
                    return s

    def run(self, metadata):
        '''
            RETURN: {
                    'value': [(ID, NAME)],              # ID = ['user', 3]
                    'query': {
                        'whereclause': [col.in_(*primary_keys)],
                        'column': [col],
                        'group_by': [col]
                    },
                    'axis_mapping': axis_map.column_mapping(result),
                    'delta':0
                }
        '''
        if self.sublevels[0].name=='all':
            return [{
                'value': [([str(self.level)], str(self.level), False)],
                'query': {
                    'column': [sqlalchemy.literal('all')],
                },
                'axis_mapping': axis_map.column_static(False),
                'delta':0,
            }]


        # Make these 2 commands working in all cases:
        # return self._run_transform(metadata)
        # return self._run_star(metadata)
        
        if self.object.table_id<>self.object.dimension_id.cube_id.table_id: # Add a condition on the object
            result = self._run_transform(metadata)
        else:
            result = self._run_star(metadata)
        return result

    def _compute_axis(self, metadata, primarykey=False):
        """
            Compute axis values, and transform the main query in the same way
            to add this branch of the star for this subset. The mappers
            reassign to values.
        """

        #
        # Build a query on all tables of the hierarchy
        # It passes the hierarchy table_id browse object (olap_cube_table )
        #
        table = common.table_get(metadata, self.object.table_id)
        #
        # Implement the query for all sublevels
        # Return:
        #     [ (ID1, ID2, ID3, NAME, [PRIMARYKEY]) ]
        #
        result_axis = {}
        for slevel in self.sublevels:
            res = slevel.run(metadata, table)
            for key in res.keys():
                result_axis.setdefault(key, [])
                result_axis[key] += res[key]
        cols = []
        axis_select = sqlalchemy.select(from_obj=[table], columns=[], distinct=True)
        for where in result_axis.get('where_clause', []):
            axis_select.append_whereclause(where)
        for col in result_axis.get('column', []):
            axis_select.append_column(col)
        for group in result_axis.get('group_by', []):
            axis_select.append_group_by(group)
        # TODO: find a way to do: axis_select2 = axis_select.copy()
        axis_select2 = sqlalchemy.select(from_obj=[table], columns=[], distinct=True)
        for where in result_axis.get('where_clause', []):
            axis_select2.append_whereclause(where)
        for col in result_axis.get('column', []):
            axis_select2.append_column(col)
        for group in result_axis.get('group_by', []):
            axis_select2.append_group_by(group)
        # TODO: end
        #metadata.bind.echo = True
        axis_select2.append_column(result_axis['column_name'][-1].label('axis_name'))
        query = axis_select2.execute()
        result = query.fetchall()
          
        def _tuple_define(x):
            y=list(x)
            if y[-1] == None:
                y[-1] = '/'
            elif isinstance(y[-1],float):
                y[-1] = str (int(y[-1]))
            else:
                y[-1] = self._to_unicode(y[-1])
                y[-1] = tools.ustr(y[-1])
            return ([self.level]+y[:-1]),y[-1]
             
        axis = map(_tuple_define, result)
        # Gives the mapping

        primary_key = ''
        if primarykey:
            if self.object.table_id.column_link_id.related_to:
                primary_key = self.object.table_id.column_link_id.related_to
            else:
                primary_key = self.object.table_id.column_link_id.table_id
            tableprim = sqlalchemy.Table(primary_key.table_db_name, metadata)
            pk = common.get_primary_key(primary_key)
            col = common.col_get(tableprim,pk)
            axis_select.append_column(col.label('axis_primarykey'))
            query = axis_select.execute()
            result = query.fetchall()
        else:
            # To find the primary key that suits best as per the given criteria
            raise 'Primary key table not made in the hierarchy'
            
        maps = []
        position =0
        for mapping in result_axis['axis_mapping']:
            mapinst = mapping(result, position)
            maps.append(mapinst)
            position += mapinst.position_get()
        result_axis['axis_mapping'] = maps
#
#       #
#       # Apply the filters on the main query object due to this block
#       #
#
#       maps = []
#       position =0
#       for mapping in result_axis['axis_mapping']:
#           mapinst = mapping(result, position)
#           maps.append(mapinst)
#           position += mapinst.position_get()
#       result_axis['axis_mapping'] = maps
#       print '*'*50
#       print table, result, result_axis
        return table, axis, result ,result_axis

    def _run_star(self, metadata):
        """
            Compute axis values, and transform the main query in the same way
            to add this branch of the star for this subset. The mappers
            reassign to values.
        """
        print '*** Start ***'
        table, result,result_mapping, result_axis = self._compute_axis(metadata, True)
        result_axis.setdefault('where_clause', [])
        #
        # The result to be applied to the main query object
        #
        result = {
            'value': result,
            'query': {
#               'whereclause': result_axis.get('where_clause',[]),
                'column': result_axis.get('column', []),
                'group_by': result_axis.get('column', [])
            },
            ##
            ## How to use group of axis_mapping ?
            ##
            'axis_mapping': axis_map.column_static(False),
            'delta':0,
        }
        return [result]

    def _run_transform(self, metadata):
        """
            Compute axis values, and transform the main query according to axis
            values for this subset. The main query slicer is transformed to a
            single condition like: foreign_key in (...) and reapplied to axis
            values.
        """

        table, axis, mapping, result_axis = self._compute_axis(metadata, True)
        table2 = common.table_get(metadata, self.object.dimension_id.cube_id.table_id)
        sql_table = sqlalchemy.Table(self.object.table_id.column_link_id.table_id.table_db_name,metadata)
        col = common.col_get(sql_table, self.object.table_id.column_link_id)

        #
        # The result to be applied to the main query object
        #

        result = []
        for a in axis:
            k = tuple(list(a)[0][1:])
            mapping_axis = filter(lambda m: tuple(list(m)[:-1])==k, mapping)
            primary_keys = map(lambda x:list(x)[-1], mapping_axis)
            # To convert everything in to the string so that no conversion needed at later stage 
            # This is for the elements to be displayed in the rows and columns
            for i in range(len(a[0])):
                if a[0][i]:
                    if isinstance(a[0][i],int):
                        a[0][i] = str(a[0][i])
                    elif isinstance(a[0][i],float):
                        a[0][i] = str(int(a[0][i]))
                else:
                    a[0][i] = '/'
            a = list(a)
            if isinstance(a[-1],int):
                a[-1] = str(a[-1])
            elif isinstance(a[-1],float):
                a[-1] = str(int(a[-1]))
            a = tuple(a)
            primary_keys = map(lambda x: str(x),primary_keys)
            result.append( {
                'value': [a],
                'query': {
                          
                    'whereclause': [col.in_(primary_keys)],#.extend(result_axis['where_clause']),
                    'column': [sqlalchemy.literal('transform')],
                },
                'axis_mapping': axis_map.column_static(False),
                'delta':0,
            })
        return result

    def __repr__(self):
        res= '\t\t<olap.level \n'
        res+= '\t\t\t'+str(self.level)+'\n'
        for l in self.sublevels:
            res+= '\t\t\t'+str(l)+'\n'
        res += '\t\t>'
        return res

class level_filter(object):
    def __init__(self, name):
        self.name=name
        self.object=None

    def validate(self, level):
        self.object = level
        return 1

    #
    # Modify for the query select to return tuples:
    #   (id, name)
    # where:
    #   id: ["Time","2008","Q1"]
    #   name: Quarter 1
    # Return a description of what have been added
    #
    def run(self, metadata, table):
        return self.object._types[self.object.type].run( self, metadata, table)

    def __repr__(self):
        return '<olap.level_filter '+self.name+'>'

class level_function(object):
    def __init__(self, name):
        self.type='function'
        self.name = name
        self.object = None
    # [{
    #   'level': ["Time","2008","Q1"],
    #   'value': '1er Trim 2008',
    #   'query': SQLAlchemy query object
    # }]
    def run(self, metadata, table):
        return self.object._types[self.object.type].children( self, metadata, table)

    def validate(self, level):
        self.object = level
        return 0

    def __repr__(self):
        return '<olap.level_function '+self.name+'>'

# vim: ts=4 sts=4 sw=4 si et
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
