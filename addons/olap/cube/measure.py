
import sqlalchemy
import common
import copy
import pyparsing
import operator
from operator import add,sub
from pyparsing import *

from agregator import agregator
import axis_map

class measure(object):
    def __init__(self, name):
        self.name = name
        self.object = False
    def validate(self, cube):
        for measure in cube.measure_ids:
            if measure.name==self.name:
                self.object = measure
        if not self.object:
            raise 'This measure does not exist !'
        return True

    def run(self, metadata):
        table = common.table_get(metadata, self.object.cube_id.table_id)
        if self.object.measure_type == 'fact_column':
            col = common.col_get(sqlalchemy.Table(self.object.table_name,metadata), self.object.value_column)
            col_agregated = agregator[self.object.agregator](col)
        else:
            scalar = Word(alphanums+"_"+" "+".") 
            sql_func = ["sum","max","min","count","avg"]
            arith_operator = ["-","*","/","+"]
            
            sql_function = oneOf(' '.join(sql_func))
            leftRdBr = Literal("(").suppress()
            rightRdBr = Literal(")").suppress()
            operator_arith = oneOf(' '.join(arith_operator))
            sqlexpression = sql_function.setResultsName('sql_func') + leftRdBr + delimitedList(scalar,",",combine=False) + rightRdBr | sql_function + leftRdBr +  scalar + ZeroOrMore(operator_arith.setResultsName('arithmetic') + scalar) + rightRdBr 
            res = sqlexpression.parseString(self.object.value_sql)
            operators = []
            cols = []
            function = None
            for item in res:
                if str(item) == res.sql_func:
                    function = str(item)
                elif str(item) == res.arithmetic or str(item) in ["+","-","/","*"]:
                    operators.append(str(item))
                else:
                    cols.append(common.measure_sql_exp_col(metadata,str(item)))
            operations = {
                '+':operator.add,
                '-':operator.sub,
                '/':operator.div,
                '%':operator.mod,
                '*':operator.mul,
            }
            operators = [operations[name] for name in operators]
            ops_cols = zip(operators, cols[1:])
            col = reduce(lambda expr, op_col: op_col[0](expr, op_col[1]), ops_cols,cols[0]) 

            if function:
                col_agregated = agregator[function](col)
            else:
                col_agregated = col

        return [ {
            'value': [(['measures',self.name], self.name, False)],
            'query': {
                'column': [col_agregated]
            },
            'axis_mapping': axis_map.column_fixed(0),
            'delta': 0,
            'format':self.object.formatstring
        } ]

    def children(self, level, metadata):
        raise 'Not yet implemented !'

    def __repr__(self):
        res= '\t\t<olap.measure %s>\n' % (self.name,)
        return res

# vim: ts=4 sts=4 sw=4 si et
