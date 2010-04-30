"""
Tiny BI
Copyright (C)2007 Fabien Pinckaers

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation version 2.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

from pyparsing import *

import cube, axis, measure, level, query, slicer, cross
import mdx_operator


#
# Predicate: the construction of the object's query does not depend
# on the schema architecture. I think we can go on for this, this will
# simplify the extension/module architecture.
#
# Rethink about that in one month.
#

class mdx_parser(object):
    def mdx_level(self):
        """
            Return a parser that parse the level part of the MDX query and
            return a level object
            Examples:
                [prod].[all prod].children
                [prod].[all prod].join(...)
        """
        leftSqBr = Literal("[").suppress()
        rightSqBr = Literal("]").suppress()
        dotToken = Literal(".").suppress()
        measuresToken = Literal("measures").suppress()
        scalar = Word(alphanums+alphas8bit.encode("utf-8") +"_"+" "+"-" )
        level_filter = leftSqBr + scalar + rightSqBr
        level_function = Keyword("children", caseless=True)
        level_filter.setParseAction(lambda s,a,toks: level.level_filter(toks[0]))
        level_function.setParseAction(lambda s,a,toks: level.level_function(toks[0]))
        level_item = level_filter | level_function
        level_parse = leftSqBr + scalar + rightSqBr + Optional(dotToken + delimitedList(level_item, ".", combine=False))
        level_parse.setParseAction(lambda s,a,toks: level.level(toks[0], toks[1:]))
        measure_parse = leftSqBr + measuresToken + rightSqBr + dotToken + leftSqBr + scalar + rightSqBr
        measure_parse.setParseAction(lambda s,a,toks: measure.measure(toks[0]))
        lev = measure_parse | level_parse
        return lev


    def mdx_axis(self):
        """
            Return a parser that parse the axis part of the MDX query and 
            return an axis object
            Examples:
                {[prod].[all prod].children, [a]}
                OR 
                crossjoin({[Order Date].[all]},{[prod].[all prod].children, [a]})
                This is to be made recursive for the cross join
                crossjoin(crossjoin({[City].[all],[City].children},{[User].[all]}),{[User].[Administrator]})

        """
        leftCurlBr = Literal("{").suppress()
        rightCurlBr = Literal("}").suppress()
        comma = Literal(",").suppress()

        level_parse = self.mdx_level()
        axis_parser = delimitedList(level_parse, ",", combine=False)
        axis_parser.setParseAction(lambda s,a,toks:axis.axis(mdx_operator.mdx_set(toks)))

        mdx = leftCurlBr + axis_parser + rightCurlBr
        
        return mdx

    def cross_axis(self):
        leftCurlBr = Literal("{").suppress()
        rightCurlBr = Literal("}").suppress()
        cross_parser = self.mdx_level()
        cross_parser.setParseAction(lambda s,a,toks:cross.cross(toks))

        cross_parse = leftCurlBr + cross_parser + rightCurlBr

        return cross_parse 
        
    def mdx_cross_axis(self):
        leftRoundBr = Literal("(").suppress()
        rightRoundBr = Literal(")").suppress()
        comma = Literal(",").suppress()
        crossjoinToken = Keyword("crossjoin", caseless=True).suppress() 
        
        crossx = Forward() 
        cross_mdx = crossx | self.mdx_axis() 
        crossx << (crossjoinToken + leftRoundBr +  cross_mdx + comma + self.cross_axis()  + rightRoundBr)
#        crossx.setParseAction(lambda s,a,toks:axis.axis(toks)
        simple_mdx = self.mdx_axis()

        mdx = simple_mdx | crossx
        return mdx  

    def mdx_axis_list(self):
        #
        # TODO: accept notation line AXIS(0) = rows, AXIS(1)=columns, ...
        #
        row_names = ["rows","columns","pages"]
        onToken = Keyword("on", caseless=True).suppress()
        page_name = oneOf(' '.join(row_names))
        axis_parser = self.mdx_cross_axis() + Optional(onToken + page_name)

        def _assign_name(s,a,toks):
            if len(toks)>=3:
                toks[0].name_set(toks[-1])
                for x in range(1,len(toks)-1):
                    toks[x].name_set('cross')
            elif len(toks)==2:
                toks[0].name_set(toks[1])
            elif len(toks)==1:
                toks[0].name_set(row_names.pop(0))
            else:
                raise 'invalid size'
            return toks[:-1]
        axis_parser.setParseAction(_assign_name)
        axis_lst = delimitedList(axis_parser, ",")
        axis_lst.setParseAction(lambda s,a,toks: [toks])
        return axis_lst
    
    def mdx_slice(self):
        """ Return a MDX parser of the where clause of a MDX query """
        leftBr = Literal("(").suppress()
        rightBr = Literal(")").suppress()
        levels = delimitedList(self.mdx_level(), ',', combine=False)
        levels.setParseAction(lambda s,a,toks: toks)
        slicer_lst = delimitedList(leftBr + levels + rightBr, ",", combine=False)
        slicer_lst.setParseAction(lambda s,a,toks:slicer.slicer(list(toks)))
        return slicer_lst
    
    def mdx_cube(self):
        """ Return a MDX parser of the from clause of a MDX query """
        mdx = Word(alphas+'_')
        mdx.setParseAction(lambda s,a,toks: cube.cube(toks[0]))
        return mdx
    
    def mdx_query(self):
        """ Return a MDX parser of the from clause of a MDX query """
        selectToken = Keyword("select", caseless=True).suppress()
        fromToken = Keyword("from", caseless=True).suppress()
        whereToken = Keyword("where", caseless=True).suppress()
        semicolon = Literal(";").suppress()
        mdx = selectToken + self.mdx_axis_list() + fromToken + self.mdx_cube() + Optional(whereToken + self.mdx_slice()) + Optional(semicolon)
        mdx.setParseAction(lambda s,a,toks: query.query(*toks))
        return mdx
    
    def parse(self, query):
        """ Parse a string and get a MDX object """
        return self.mdx_query().parseString(query)[0]

if __name__ == "__main__":
    mdx = mdx_parser()
    level_parse = mdx.mdx_level()
    for test in ['[sales].children','[prod].[all prod]']:
        print 'Testing level', test
        print level_parse.parseString(test)
    print
    axis_parser = mdx.mdx_axis()
    for test in ['{[a]}','{[prod].[all prod],[time].[Q3].[Sep]}']:
        print 'Testing axis', test
        print axis_parser.parseString(test)

    axis_parser = mdx.mdx_axis_list()
    for test in ['{[a]} on rows, {[prod].[all prod],[time].[Q3].[Sep]} on columns',
        '{[region].[all region].children} on rows, {[prod].[all prod].children} on columns'
    ]:
        print 'Testing axis', test
        print axis_parser.parseString(test)

    cube_parser = mdx.mdx_cube()
    for test in ['sales']:
        print 'Testing axis', test
        print cube_parser.parseString(test)

    for query_parser in [
"Select {[region].[all region].children} on rows, {[product]} on columns from cubulus where ([time].[all time].[time_2005])",
"Select {[region].[all region].children} on rows, {[prod].[all prod].children} on columns from cubulus where ([time].[all time].[time_2005])",
#"Select {[time].[all time].children} on rows, crossjoin([region].[all region].children, [region].[all region].children) on columns from cubulus"
    ]:
        print 'Testing ', query_parser
        print mdx.parse(query_parser)

    print mdx.parse('''select
            {[date].[2007].[Q2].children} on rows, 
            {[country_id].children,[country_id].[1].children} on columns 
        from res_partner where ([measure].[credit_limit])''')
# vim: ts=4 sts=4 sw=4 si et
