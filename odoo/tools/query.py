# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
This python module contains a high-level abstraction for building SQL queries,
the generated SQL statements are specific to the PostgreSQL idiom since it's what Odoo uses,
therefore it is guaranteed to work with PostgreSQL, however it may still work with other RDBMS,
but this is not guaranteed.

Usage:

The basic object needed for creating SQL statements and expressions is the `Row` object, it
represents a row from a table, it requires one argument for initialization which is the name of
the table containing such row.

e.g.:
    >>> res_partner = Row('res_partner')

Proper identifier quoting is done automatically by the AST and its elements, therefore there is no
need for whoever uses the tool to explicitly quote an identifier, and in fact this will raise
a ValueError, this is done to avoid SQL Injections to the best of our ability.

One can access a row's columns by using pythonic attribute getting / dot notation.

e.g.:
    >>> col = res_partner.id

Columns are created on-the-fly, meaning that they are created as the Row object's attributes
are being accessed, this means that two column accesses will never have the same identity!

Note that these objects are not DB-validated, meaning that one could create a Row object of a
table that does not exist in DB, or access a column that does not exist in a table's schema, the
performance cost of this kind of validation does not warrant its use-case, it is to be used
with caution as the "validation" will be done by Postgres itself.

Once a row object is created, one can perform pythonic expressions with its columns,
these expressions can then be translated into SQL expressions.

e.g.:
    >>> expr = res_partner.id == 5
    >>> expr._to_sql(None)
    ... ('("res_partner"."id" = %s)', [5])

Two things to note from the previous example:
    * Expressions are automatically parenthesized.

    * Literals are not directly interpolated into the SQL string, instead string interpolation
      placeholders are put in their place and the actual literals are appended to a list of
      arguments (order matters!). This tuple can then be passed directly to cr.execute(), which
      will properly perform the interpolation without the risk of SQL-Injections.

Rows, Columns and Expressions are the building blocks of the query builder, but they're
pretty useless by themselves, to create meaningful SQL statements, one should use
the Select, Insert, Update, Delete, etc. classes for creating the corresponding SQL statements,
in order to see their usage, consult the respective class' documentation.
"""

from collections import OrderedDict
from functools import partial

from .misc import OrderedSet


def _quote(val):
    """ Helper function for quoting SQL identifiers."""
    if '"' not in val:
        return '"%s"' % val
    raise ValueError("The string to be quoted must not already contain quotes.")


def generate_aliases():
    # XXX: Increase the amount of possible table aliases
    return iter('abcdefghijklmnopqrstuvwxyz')


class Expression(object):

    """
    Main Abstract Syntax Tree of the query builder.

    Args:
        op (str): The operation of the expression.
        left: The left operand of the expression.
        right: The right operand of the expression.

    Valid expressions:
        a & b  -> a AND b
        a | b  -> a OR b
        ~a     -> NOT a
        a == b -> a = b
        a != b -> a != b
        a < b  -> a < b
        a <= b -> a <= b
        a > b  -> a > b
        a >= b -> a >= b
        a.in_(b)  -> a IN b
        a.like(b)  -> a LIKE b
        a.ilike(b) -> a ILIKE b
    """

    __slots__ = ('left', 'op', 'right')

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __and__(self, other):
        assert isinstance(other, Expression), "`&` operands must be Expressions."
        return Expression('AND', self, other)

    def __or__(self, other):
        assert isinstance(other, Expression), "`|` operands must be Expressions."
        return Expression('OR', self, other)

    def __invert__(self):
        return Expression('NOT', self, None)

    def __eq__(self, other):
        if other is None or other is NULL:
            return Expression('IS', self, NULL)
        return Expression('=', self, other)

    def __ne__(self, other):
        if other is None or other is NULL:
            return Expression('IS NOT', self, NULL)
        return Expression('!=', self, other)

    def __lt__(self, other):
        return Expression('<', self, other)

    def __le__(self, other):
        return Expression('<=', self, other)

    def __gt__(self, other):
        return Expression('>', self, other)

    def __ge__(self, other):
        return Expression('>=', self, other)

    def __add__(self, other):
        return Expression('+', self, other)

    def __sub__(self, other):
        return Expression('-', self, other)

    def __mul__(self, other):
        return Expression('*', self, other)

    def __truediv__(self, other):
        return Expression('/', self, other)

    def __pow__(self, other):
        return Func('pow', self, other)

    def __mod__(self, other):
        return Func('mod', self, other)

    def __abs__(self):
        return Func('abs', self)

    def like(self, other):
        return Expression('LIKE', self, other)

    def ilike(self, other):
        return Expression('ILIKE', self, other)

    def in_(self, other):
        # Optimization
        if isinstance(other, tuple) and not other:
            raise ValueError("Cannot perform IN operation on an empty tuple.")
        return Expression('IN', self, other)

    @property
    def rows(self):
        """Return an OrderedSet containing all the rows of an expression via recursion."""
        res = OrderedSet()
        nodes = [getattr(self, 'left', None), getattr(self, 'right', None)]

        for node in nodes:
            if isinstance(node, Expression):
                res |= node.rows

        if hasattr(self, '_row'):
            res.add(self._row)

        return res

    def _to_sql(self, alias_mapping):
        """
        Generates a string representation for the current AST expression.

        Returns:
            A tuple containing an SQL string and a list of arguments that cannot be directly
            interpolated into the string for security reasons, to be fed directly into cr.execute()
        """
        # TODO: Optimize parentheses generation
        left, args = self.left._to_sql(alias_mapping)

        if self.op == 'NOT':
            # Unary
            return ("(NOT %s)" % left, args)

        # Binary
        sql = "({left} {op} {right})"

        if isinstance(self.right, Expression):
            # Another AST expression
            right, _args = self.right._to_sql(alias_mapping)

            if isinstance(self.right, Select):
                # Sub-queries must be parenthesized
                right = '(%s)' % right

            args += _args
        else:
            # Literal or Constant
            if self.right is NULL:
                right = self.right
            else:
                right = "%s"
                args.append(self.right)

        return (sql.format(left=left, op=self.op, right=right), args)


class Case(Expression):

    def __init__(self, cases, default=None, expr=None):
        """
        Generates a `CASE WHEN` SQL expression.

        Arguments:
            cases: List of tuples, each containing two elements, the first being the
                expression for the WHEN clause and the second one being the expression for the
                THEN clause.
            default: Expression for the ELSE clause.
            expr: Optional expression between the CASE and the WHEN clauses.
        """
        self.cases = cases
        self.default = default
        self.expr = expr

    @property
    def rows(self):
        """Returns an OrderedSet containing all the rows appearing in the Case expression."""
        rows = OrderedSet()

        for when, then in self.cases:
            if isinstance(when, Expression):
                rows |= when.rows
            if isinstance(then, Expression):
                rows |= then.rows

        if self.expr:
            rows |= self.expr.rows

        return rows

    def _to_sql(self, alias_mapping):
        sql = ['CASE']
        args = []

        if self.expr:
            _sql, _args = self.expr._to_sql(alias_mapping)
            sql.append(_sql)
            args += _args

        for when, then in self.cases:
            _sql = "WHEN %s THEN %s"

            if isinstance(when, Expression):
                when_sql, when_args = when._to_sql(alias_mapping)
            else:
                when_sql = "%s"
                when_args = [when]

            if isinstance(then, Expression):
                then_sql, then_args = then._to_sql(alias_mapping)
            else:
                then_sql = "%s"
                then_args = [then]

            sql.append(_sql % (when_sql, then_sql))
            args += when_args + then_args

        if self.default:
            if isinstance(self.default, Expression):
                _sql, _args = self.default._to_sql(alias_mapping)
            else:
                _sql = "%s"
                _args = [self.default]

            sql.append("ELSE %s" % _sql)
            args += _args

        sql.append("END")

        return (' '.join(sql), args)


class Row(object):

    __slots__ = ('_table', '_cols')

    def __init__(self, table):
        """
        Create an object that represents a table's row.

        Args:
            table (str): Name of the table.
        """
        self._table = _quote(table)
        self._cols = OrderedDict()

    @property
    def rows(self):
        return OrderedSet([self])

    def __call__(self, *args):
        # For insert queries, used to define the columns that the specified values to be
        # inserted apply to.
        for col in args:
            self._cols[col] = Column(self, col)
        return self

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError
        if name in self._cols:
            return self._cols[name]
        return Column(self, name)

    def _to_sql(self, alias_mapping, with_cols=False):
        if with_cols:
            if self._cols:
                return "%s(%s)" % (self._table,
                                   ', '.join([c._name for c in self._cols.values()])), []
            return "%s" % self._table, []
        return "%s %s" % (self._table, alias_mapping[self]), []


class Column(Expression):

    __slots__ = ('_row', '_name')

    def __init__(self, row, name):
        """
        A Row object's column.

        Should rarely be instantiated by the user, the Row class should be used instead as a proxy
        for Column objects.

        Args:
            row (Row): Row that this column belongs to (table).
            name (str): Name of the column.
        """
        self._row = row
        self._name = _quote(name)

    def __hash__(self):
        return hash((self._row, self._name))

    def _to_sql(self, alias_mapping=None, val=None):
        qualified = "{}.%s" % self._name
        row = self._row

        if alias_mapping is not None and val is None:
            col_name = qualified.format(alias_mapping[row])
        elif val is not None:
            col_name = self._name
        else:
            col_name = qualified.format(row._table)

        if val is not None:
            # for update/set queries
            if isinstance(val, Column):
                # col = col
                _sql, _args = val._to_sql(alias_mapping)
                return "%s = %s" % (col_name, _sql), _args
            elif isinstance(val, Expression):
                # col = sub-select/func/expression
                _sql, _args = val._to_sql(alias_mapping)
                return "%s = (%s)" % (col_name, _sql), _args
            # col = literal value
            return "{} = %s".format(col_name), [val]
        return col_name, []


class BaseQuery(Expression):

    __slots__ = ('sql', 'args', '_rows', '_returning', '_where')

    def __init__(self, *args, **kwargs):
        """
        Helper class for combining the different parts of any Query object.

        All the _build_* methods are called in the _build_all() method which itself
        is called from the _to_sql method, all these methods take in an alias_mapping argument
        which is an AliasMapping object, in order to determine potential table aliases.

        All query classes (Select, Insert, Delete, ...) inherit from this one class in order
        to generate their own SQL statements, some may override already-defined _build methods,
        some may override _to_sql as they might have very specific behavior.
        """
        self._rows = []
        self._returning = []
        self._where = None
        self.sql = []
        self.args = []

    def __hash__(self):
        return hash(tuple(self._rows + self._returning + self.sql + self.args) + (self._where,))

    def __getattr__(self, name):
        # Query objects can be used as rows.
        if name.startswith('__'):
            raise AttributeError
        return Column(self, name)

    @property
    def rows(self):
        return OrderedSet()

    def _build_base(self, alias_mapping):
        """
        Builds the basic part of the query, the identifying part.

        This part is mandatory for all queries.

        Examples:
            For the select query, the base would be "SELECT"
            For the insert query, the base would be "INSERT INTO x"
        """
        raise NotImplementedError

    @property
    def attrs(self):
        """
        The arguments required for instantiation of a BaseQuery sub-class.

        Mandatory for all queries.
        """
        raise NotImplementedError

    def copy(self):
        """
        Creates a copy of any BaseQuery sub-class.

        Used mainly for the WITH query.
        """
        return self.__class__(**self.attrs)

    def _build_from(self, alias_mapping):
        sql = []
        for row in self._rows:
            if isinstance(row, BaseQuery):
                _sql, _args = row._to_sql(AliasMapping())
                sql.append("(%s) %s" % (_sql, alias_mapping[row]))
            else:
                _sql, _args = row._to_sql(alias_mapping)
                sql.append(_sql)
            self.args += _args

        if sql:
            self.sql.append("FROM %s" % ', '.join(sql))

    def _build_joins(self, alias_mapping):
        pass

    def _build_using(self, alias_mapping):
        pass

    def _build_where(self, alias_mapping):
        if self._where is not None:
            sql, args = self._where._to_sql(alias_mapping)
            self.sql.append("WHERE %s" % sql)
            self.args += args

    def _build_order(self, alias_mapping):
        pass

    def _build_group(self, alias_mapping):
        pass

    def _build_having(self, alias_mapping):
        pass

    def _build_limit(self, alias_mapping):
        pass

    def _build_on_conflict(self, alias_mapping):
        pass

    def _build_returning(self, alias_mapping):
        args = []
        sql = []

        for e in self._returning:
            if isinstance(e, Row):
                sql.append('*')
                break
            else:
                # Column or Expression
                _sql, _args = e._to_sql(alias_mapping)
                sql.append(_sql)
                args += _args

        if sql:
            self.sql.append("RETURNING %s" % ', '.join(sql))
            self.args += args

    def _build_all(self, alias_mapping):
        # Order matters!!
        self._build_base(alias_mapping)
        self._build_from(alias_mapping)
        self._build_joins(alias_mapping)
        self._build_using(alias_mapping)
        self._build_where(alias_mapping)
        self._build_order(alias_mapping)
        self._build_group(alias_mapping)
        self._build_having(alias_mapping)
        self._build_limit(alias_mapping)
        self._build_on_conflict(alias_mapping)
        self._build_returning(alias_mapping)

    def _to_sql(self, alias_mapping):
        self._build_all(alias_mapping)
        self.sql = [sql for sql in self.sql if sql]
        res = ' '.join(self.sql), tuple(self.args)
        self.sql = []
        self.args = []
        return res

    def to_sql(self):
        return self._to_sql(AliasMapping())


class AliasMapping(dict):

    def __init__(self, *args, **kwargs):
        """
        A special implementation of dict that generates appropriate table aliases on the fly.

        Keys must be Row or pseudo-Row objects (sub-selects), if the key is missing
        from the AliasMapping, it will be added to the AliasMapping and an alias will be assigned
        to it, the alias is a single letter from the alphabet that is double-quoted.

        If the key is already in the AliasMapping, then we will simply return its corresponding
        alias.

        Some constructs don't use or reset aliases:

            * WITH statements will define a table but not give it any aliases, the table is called
              by its fully-qualified name.

            * SELECT query expressions (UNION, INTERSECT, EXCEPT) won't use the same AliasMapping
              for both of their operands, i.e. each operand's first table will be "a".

            * Sub-queries use a different AliasMapping than the one of its encompassing query.
        """
        super(AliasMapping, self).__init__()
        self._generator = generate_aliases()

    def __missing__(self, k):
        alias = _quote(next(self._generator))
        self[k] = alias
        return alias


class Join(object):

    def __init__(self, main, join, condition=None, _type='inner'):
        """
        Create a join between two tables on a given condition.

        Args:
            main (Row): the main row of the join.
            join (Row): the row to join.
            condition (Expression): an AST expression which will serve as the ON condition for the
                Join, if not specified then there will be no condition (ON TRUE).
            _type (str): the type of the join, possible values are 'inner', 'left', 'right' and
                'full'. (default: 'inner')
        """
        self._main = main
        self._join = join
        self._condition = condition
        permitted_types = ['inner', 'full', 'left', 'right']
        assert _type in permitted_types, "Join type must be one of (inner, full, left, right)"
        self._type = _type.upper()

    def _to_sql(self, alias_mapping):
        sql = "%s JOIN %s"
        args = []

        if isinstance(self._join, BaseQuery):
            _join_sql, _join_args = self._join._to_sql(AliasMapping())
            _join_sql = "(%s) %s" % (_join_sql, alias_mapping[self._join])
        else:
            _join_sql, _join_args = self._join._to_sql(alias_mapping)

        args += _join_args

        if self._condition:
            sql += " ON %s"
            _sql, _args = self._condition._to_sql(alias_mapping)
            return (sql % (self._type, _join_sql, _sql), args + _args)
        return (sql % (self._type, _join_sql), args)


class Modifier(object):

    def __init__(self, column, modifier, nfirst=False):
        """
        Appends the specified modifier to the result of column._to_sql()

        Args:
            column (Column): The column to be modified.
            modifier (str): The modifier itself.
            nfirst (bool): Whether `NULLS FIRST` should be specified (default: False)
        """
        assert isinstance(column, Column), "Modifier requires a column!"
        self.column = column
        self.modifier = modifier
        self.nfirst = nfirst

    def _to_sql(self, alias_mapping):
        sql, args = self.column._to_sql(alias_mapping)
        sql += " %s " % self.modifier
        sql += "NULLS FIRST" if self.nfirst else "NULLS LAST"
        return sql, args


class Asc(Modifier):

    """ Ascending order """

    def __init__(self, column, nulls='last'):
        super(Asc, self).__init__(column, 'ASC', nulls == 'first')


class Desc(Modifier):

    """ Descending order """

    def __init__(self, column, nulls='last'):
        super(Desc, self).__init__(column, 'DESC', nulls == 'first')


class Query(object):

    """
    Proxy class for creating SQL queries in a functional programming style.
    """

    @staticmethod
    def select(*args):
        return Select(args)

    @staticmethod
    def delete(*args):
        return Delete(args)

    @staticmethod
    def update(_set):
        return Update(_set)

    @staticmethod
    def insert(row, vals):
        return Insert(row, vals)


class Select(BaseQuery):

    __slots__ = (
        '_columns', '_order', '_joins', '_distinct', '_group', '_having', '_limit',
        '_offset', '_aliased', '_from',
    )

    def __init__(self, columns, where=None, order=None, joins=None, distinct=False,
                 group=None, having=None, limit=None, offset=0, _from=None):
        """
        Class for generating SQL SELECT statements.

        Args:
            columns: This argument can take multiple forms:
                * A list of columns, in this case no columns will be aliased.
                * A mapping of (alias, column), in this case all columns with a string as key
                    will have the string as their alias, if the key is an integer then it will
                    not have an alias. Use OrderedDict if the order of the columns is important.
                * A single-element list containing a Row object, in this case all the columns
                    of the Row will be selected, equivalent to SELECT *, if there is more than
                    one element in the list, all others will be ignored.
            where (Expression): Expression for filtering out the results of the query.
            order: List of (potentially modified) columns to order by.
            joins: List of Join objects.
            distinct: This argument can take multiple forms:
                * A boolean value, True meaning distinct on the whole query, False meaning
                    no distinct at all. (default: False)
                * A column, meaning that only that column must be unique.
                * A list of columns, all of which must be unique.
            group: List of columns to order by.
            having (Expression): Condition for the group by.
            limit (int): Maximum amount of records to fetch.
            offset (int): Skip the first X records when performing a Select with a limit,
            has no effect if limit is not specified. (default: 0)

        Example:
            p = Row('res_partner')
            u = Row('res_users')
            s = Select({'id': p.id}, p.name != None, [Desc(p.id)],
                       [Join(self.p, self.u, p.id == u.partner_id, 'left')])
            >>> s._to_sql()

            SELECT "res_partner"."id" AS id
            LEFT JOIN "res_users" ON "res_partner"."id" = "res_users"."partner_id"
            WHERE ("res_partner"."name" IS NOT NULL)
            ORDER BY "res_partner"."id" DESC NULLS LAST
        """
        super(Select, self).__init__()

        self._columns = columns
        self._where = where
        self._order = order or []
        self._joins = joins or []
        self._distinct = distinct
        self._group = group or []
        self._having = having
        self._limit = limit
        self._offset = offset
        self._from = OrderedSet([_from]) if _from is not None else OrderedSet([])
        self._aliased = isinstance(columns, dict)

        # Joins must be exclusively implicit or explicit
        # Good:
        #   * FROM a, b ...
        #   * FROM a, b, c ...
        #   * FROM a INNER JOIN b ...
        #   * FROM a INNER JOIN b ON TRUE INNER JOIN c ...
        # Bad:
        #   * FROM a, b INNER JOIN c ...
        # There's no error-checking, but the resulting query won't be what the user expects!
        self._rows = self._get_tables()

    @property
    def attrs(self):
        return {
            'columns': self._columns,
            'where': self._where,
            'order': self._order,
            'joins': self._joins,
            'distinct': self._distinct,
            'group': self._group,
            'having': self._having,
            'limit': self._limit,
            'offset': self._offset,
        }

    def _get_tables(self):
        columns = []

        # Normalize arguments
        # XXX: Do in __init__ ?
        if self._aliased:
            columns += list(self._columns.values())
        else:
            columns += self._columns

        tables = self._from

        for col in columns:
            try:
                tables |= col.rows
            except Exception:
                # Literals have no tables
                pass

        if self._where is not None:
            tables |= self._where.rows

        tables_to_join = OrderedSet([j._join for j in self._joins])

        tables -= tables_to_join
        return list(tables)

    # Select query operations
    def union(self, other):
        return QueryExpression('UNION', self, other)

    def union_all(self, other):
        return QueryExpression('UNION ALL', self, other)

    def intersect(self, other):
        return QueryExpression('INTERSECT', self, other)

    def intersect_all(self, other):
        return QueryExpression('INTERSECT ALL', self, other)

    def ex(self, other):
        return QueryExpression('EXCEPT', self, other)

    def ex_all(self, other):
        return QueryExpression('EXCEPT ALL', self, other)

    # Select query operation shortcuts
    def __or__(self, other):
        return self.union(other)

    def __and__(self, other):
        return self.intersect(other)

    def __sub__(self, other):
        return self.ex(other)

    # Generation of new Select objects
    def columns(self, *cols):
        """ Create a similar Select object but with different output columns."""
        return Select(**{**self.attrs, 'columns': cols})

    def distinct(self, expressions):
        """ Create a similar Select object but toggle the distinct flag."""
        return Select(**{**self.attrs, 'distinct': expressions})

    def where(self, expression):
        """ Create a similar Select object but with a different where clause."""
        return Select(**{**self.attrs, 'where': expression})

    def join(self, *expressions):
        """ Create a similar Select object but with different joins."""
        return Select(**{**self.attrs, 'joins': expressions})

    def order(self, *expressions):
        """ Create a similar Select object but with a different order by clause."""
        return Select(**{**self.attrs, 'order': expressions})

    def group(self, *expressions):
        """ Create a similar Select object but with a different group by clause."""
        return Select(**{**self.attrs, 'group': expressions})

    def having(self, expression):
        """ Create a similar Select object but with a different having clause. """
        return Select(**{**self.attrs, 'having': expression})

    def limit(self, n):
        """ Create a similar Select object but with a different limit."""
        return Select(**{**self.attrs, 'limit': n})

    def offset(self, n):
        """ Create a similar Select object but with a different offset."""
        return Select(**{**self.attrs, 'offset': n})

    def _build_base(self, alias_mapping):
        sql = ["SELECT"]
        args = []

        if self._distinct:
            sql.append(self._build_distinct(alias_mapping))

        _sql = []
        for c in self._columns:
            # Type normalization
            # XXX: Do in __init__ ?
            val = c if not self._aliased else self._columns[c]
            alias = " AS %s" % c if self._aliased and not isinstance(c, int) else ""

            if isinstance(val, Row):
                # All
                _sql.append("*")
            else:
                if isinstance(val, (Case, BaseQuery)):
                    # Sub-query / Sub-statement
                    __sql, _args = val._to_sql(AliasMapping())
                    _sql.append("(%s)%s" % (__sql, alias))
                    args += _args
                elif isinstance(val, Func) and val.func == 'unnest':
                    _sql.append(alias_mapping[val])
                else:
                    # Common case
                    try:
                        __sql, _args = val._to_sql(alias_mapping)
                    except Exception:
                        # Literal
                        __sql, _args = "%s", [val]
                    finally:
                        _sql.append("%s%s" % (__sql, alias))
                        args += _args

        sql.append(', '.join(_sql))
        self.sql.append(' '.join(sql))
        self.args += args

    def _build_distinct(self, alias_mapping):
        if isinstance(self._distinct, bool):
            return "DISTINCT"
        elif isinstance(self._distinct, Column):
            return "DISTINCT ON (%s)" % self._distinct._to_sql(alias_mapping)[0]
        else:
            return "DISTINCT ON (%s)" % ', '.join(
                [d._to_sql(alias_mapping)[0] for d in self._distinct])

    def _build_joins(self, alias_mapping):
        args = []
        sql = []

        for join in self._joins:
            _sql, _args = join._to_sql(alias_mapping)
            sql.append(_sql)
            args += _args

        self.sql.append(' '.join(sql))
        self.args += args

    def _build_order(self, alias_mapping):
        if self._order:
            sql = "ORDER BY %s"
            self.sql.append(sql % ', '.join([o._to_sql(alias_mapping)[0] for o in self._order]))

    def _build_group(self, alias_mapping):
        if self._group:
            sql = "GROUP BY %s"
            self.sql.append(sql % ', '.join([g._to_sql(alias_mapping)[0] for g in self._group]))

    def _build_having(self, alias_mapping):
        if self._having:
            sql = "HAVING %s"
            having, args = self._having._to_sql(alias_mapping)
            self.sql.append(sql % having)
            self.args += args

    def _build_limit(self, alias_mapping):
        if self._limit:
            sql = "LIMIT %s OFFSET %s"
            self.sql.append(sql)
            self.args += [self._limit, self._offset]


class QueryExpression(Select):

    __slots__ = ('op', 'left', 'right')

    """Class for operations between Select objects."""

    def __init__(self, op, left, right):
        assert isinstance(left, Select) and isinstance(right, Select), "Operands must be Selects."
        self.left = left
        self.op = op
        self.right = right

    def _to_sql(self, alias_mapping):
        left, largs = self.left._to_sql(alias_mapping)
        right, rargs = self.right._to_sql(AliasMapping())
        return ("(%s) %s (%s)" % (left, self.op, right), largs + rargs)

    def to_sql(self):
        return self._to_sql(AliasMapping())


class Delete(BaseQuery):

    __slots__ = ('_using')

    def __init__(self, table, using=None, where=None, returning=None):
        """
        Class for generating SQL DELETE statements.

        Args:
            table: List of Row instances of the tables from which records will be deleted.
            using: List of Row instances that may appear in the query's expressions but that
                won't be deleted from.
            where (Expression): Expression that will filter the table for records to be deleted.
            returning: List of (Expression|Column|Row) to dictate what kind of output should be
                returned after executing the query.

        Example:
            >>> r = Row('res_partner')
            >>> d = Delete([r], where=r.active == False)
            >>> d.to_sql()
            DELETE FROM "res_partner" "a" WHERE "a"."active" = 'False'
        """
        super(Delete, self).__init__()
        self._rows = table
        self._using = using or []
        self._where = where
        self._returning = returning or []

    def table(self, *rows):
        return Delete(**{**self.attrs, 'table': rows})

    def using(self, *tables):
        return Delete(**{**self.attrs, 'using': tables})

    def where(self, expr):
        return Delete(**{**self.attrs, 'where': expr})

    def returning(self, *cols):
        return Delete(**{**self.attrs, 'returning': cols})

    @property
    def attrs(self):
        return {
            'table': self._rows,
            'using': self._using,
            'where': self._where,
            'returning': self._returning,
        }

    def _build_base(self, alias_mapping):
        self.sql.append("DELETE")

    def _build_using(self, alias_mapping):
        if self._using:
            self.sql.append("USING %s" % ", ".join(
                ["%s %s" % (r._table, alias_mapping[r]) for r in self._using]
            ))


class With(BaseQuery):

    __slots__ = ('_body', '_tail', '_recur')

    def __init__(self, body, tail, recursive=False):
        """
        Class for creating WITH SQL statements (temporary tables).

        Args:
            body: List containing tuples in which the first element is a Row object, optionally
                defining _cols attribute via __call__, and the second element is an SQL query that
                returns rows with an amount of cols equivalent to the amount of _cols defined,
                if the recursive flag is True, then these queries must be UNIONs between a
                base query and a recursive query.
            tail: An SQL query that (ideally) uses the results from the WITH table to generate
                its own result.
            recursive: Whether the WITH statement is RECURSIVE or not.

        /!\ BEWARE: By PostgreSQL's doc, calling recursive terms inside data-modifying queries
            is not permitted, therefore only SELECT queries can use recursive terms. /!\
        """
        self._body = body
        # The tail must be recomputed in case a _vals attribute has been assigned since its
        # instantiation.
        self._tail = tail.copy()
        self._recur = recursive

    def _to_sql(self, alias_mapping):
        sql = []
        args = []

        for row, statement in self._body:
            _sql = []
            alias_mapping[row] = row._table
            rsql, rargs = row._to_sql(alias_mapping, with_cols=True)
            _sql.append(rsql)
            args += rargs
            __sql, _args = statement._to_sql(alias_mapping)
            _sql.append(__sql)
            args += _args
            sql.append("%s AS (%s)" % tuple(_sql))

        _sql, _args = self._tail._to_sql(AliasMapping())
        args += _args

        return ("WITH %s%s %s" % ("RECURSIVE " if self._recur else "", ', '.join(sql), _sql),
                tuple(args))

    def to_sql(self):
        return self._to_sql(AliasMapping())


class Update(BaseQuery):

    __slots__ = ('_set', '_main')

    def __init__(self, _set, where=None, returning=None):
        """
        Class for creating UPDATE SQL statements.

        Args:
            _set: Dict of columns to update as keys and the value to set as values, if order
                is important, then an OrderedDict can be passed-in.
            where (Expression): Expression that will filter out the records to Update.
            returning: List of columns that the UPDATE statement should return.

        Example:
            >>> r = Row("res_partner")
            >>> u = Update({r.name: "John", r.surname: "Wick"}, r.name == NULL, [r.id])
            >>> u.to_sql()
            ... ('UPDATE "res_partner" "a" SET "a"."name" = %s, "a"."surname" = %s WHERE \
            ... ("a"."name" IS NULL) RETURNING "a"."id"', ('John', 'Wick'))
        """
        assert bool(_set)
        super(Update, self).__init__()
        self._set = _set
        self._where = where
        self._returning = returning or []
        # The main table is the row of the cols being used as keys.
        cols = list(_set.keys())
        assert all(col._row == cols[0]._row for col in cols)
        self._main = list(_set.keys())[0]._row
        # Auxiliary tables found in set expressions
        self._rows = self._get_aux_rows()

    def _get_aux_rows(self):
        vals = list(self._set.values())
        rows = set()

        for val in vals:
            if isinstance(val, Expression):
                rows |= val.rows

        return list(rows - set([self._main]))

    @property
    def attrs(self):
        return {
            '_set': self._set,
            'where': self._where,
            'returning': self._returning,
        }

    def set(self, _set):
        return Update(**{**self.attrs, '_set': _set})

    def where(self, expr):
        return Update(**{**self.attrs, 'where': expr})

    def returning(self, *cols):
        return Update(**{**self.attrs, 'returning': cols})

    def _pre_build(self, alias_mapping):
        return "UPDATE %s %s" % (self._main._table, alias_mapping[self._main])

    def _build_base(self, alias_mapping):
        sql = [self._pre_build(alias_mapping), "SET"]
        args = []

        _set = []
        for col, val in self._set.items():
            _sql, _args = col._to_sql(alias_mapping, val)
            _set.append(_sql)
            args += _args

        _set = ', '.join(_set)
        sql.append(_set)
        self.sql.append(' '.join(sql))
        self.args += args


class Insert(BaseQuery):

    __slots__ = ('_vals', '_on_conflict', '_row')

    def __init__(self, row, vals, on_conflict=False, returning=None):
        """
        Class for creating SQL INSERT statements.

        Args:
            row (Row): The table to insert to, can be used as a callable to pass (as strings) the
                columns of the table that map to the vals argument.
            vals: List of values to map to the specified columns. If no columns are specified then
                it will implicitly assume that all the values map, in order, to all the available
                columns, managed by PostgreSQL itself.
            on_conflict: This argument can take on multiple forms:
                * False, meaning that no conflict management should be done, this is the default.
                * None, meaning that on conflict we will do nothing.
                * A two-tuple, the first element being a list of columns that can conflict and
                    the second element being an Update query object.
            returning: List of columns that the INSERT statement should return.

        Example:
            >>> p = Row("res_partner")
            >>> # in this case, only the columns name, surname and company will be defined
            >>> i = Insert(p('name', 'surname', 'company'), ['John', 'Wick', 'MyCompany'],
            ...            returning=[p.id])
            >>> i.to_sql()
            ... ('INSERT INTO "res_partner"('name', 'surname', 'company') VALUES
            ... (%s) ON CONFLICT DO NOTHING RETURNING "res_partner"."id"',
            ... ['John', 'Wick', 'MyCompany'])
        """
        super(Insert, self).__init__()
        self._row = row
        self._vals = vals
        self._on_conflict = on_conflict
        self._returning = returning or []

    @property
    def attrs(self):
        return {
            'row': self._row,
            'vals': self._vals,
            'on_conflict': self._on_conflict,
            'returning': self._returning,
        }

    def into(self, row):
        return Insert(**{**self.attrs, 'row': row})

    def values(self, *vals):
        return Insert(**{**self.attrs, 'vals': vals})

    def on_conflict(self, args):
        return Insert(**{**self.attrs, 'on_conflict': args})

    def returning(self, *cols):
        return Insert(**{**self.attrs, 'returning': cols})

    def _pre_build(self, alias_mapping):
        _sql, _args = self._row._to_sql(alias_mapping, with_cols=True)
        self.args += _args
        return """INSERT INTO %s""" % _sql

    def _build_base(self, alias_mapping):
        self.sql.append(self._pre_build(alias_mapping))
        args = []
        sql = "VALUES %s"

        if any([isinstance(x, Select) for x in self._vals]):
            assert len(self._vals) == 1, "Only one sub-query per INSERT statement allowed."
            _sql, _args = self._vals[0]._to_sql(alias_mapping)
            sql = ("(%s)" % _sql)
            self.args += _args
            self.sql.append(sql)
            return

        values = []
        for val in self._vals:
            if val is NULL or val is DEFAULT:
                values.append(str(val))
            else:
                values.append("%s")
                args.append(val)

        sql %= ("(%s)" % ', '.join(values))
        self.sql.append(sql)
        self.args += args

    def _build_on_conflict(self, alias_mapping):
        if self._on_conflict is None:
            self.sql.append("ON CONFLICT DO NOTHING")
        elif self._on_conflict:
            cols, do = self._on_conflict
            assert bool(cols), "ON CONFLICT DO UPDATE requires a conflict_target"
            assert isinstance(do, Update), "ON CONFLICT requires its conflict_action to be an\
                Update query"

            _cols_sql = []
            _cols_args = []

            for col in cols:
                _sql, _args = col._to_sql(None)
                _cols_sql.append(_sql)
                _cols_args += _args

            self.sql.append("ON CONFLICT (%s) DO" % ', '.join(_cols_sql))
            self.args += _cols_args

            _do_sql, _do_args = do._to_sql(alias_mapping)
            self.sql.append(_do_sql)
            self.args += _do_args

    def _build_returning(self, alias_mapping):
        alias_mapping[self._row] = self._row._table
        super(Insert, self)._build_returning(alias_mapping)


class CreateView(BaseQuery):

    __slots__ = ('_name', '_content', '_replace')

    def __init__(self, name, content, replace=False):
        """
        Class for creating CREATE VIEW statements.

        Args:
            name (str): Name given to the view.
            content: Either a Select object or a With object, will be used to create the content
                of the view.
            replace (bool): Whether the view should be replaced if it already exists or not.
        """
        assert isinstance(content, BaseQuery)
        super(CreateView, self).__init__()
        self._name = _quote(name)
        self._content = content
        self._replace = replace

    def _build_base(self, alias_mapping):
        self.sql.append("CREATE %sVIEW %s" % ("OR REPLACE " if self._replace else "", self._name))
        sql, args = self._content._to_sql(alias_mapping)
        self.sql.append("AS (%s)" % sql)
        self.args += args


# SQL Constants
class Constant(object):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


NULL = Constant('NULL')
DEFAULT = Constant('DEFAULT')


# SQL Functions and Aggregates
class Func(Expression):

    __slots__ = ('func', 'args')

    def __init__(self, func, *args):
        """
        Generic PostgreSQL Aggregate/Function, accepts any amount of arguments.

        Args:
            func (str): Name of the function
            args: The function's arguments
        """
        self.func = func
        self.args = args

    def __key(self):
        return hash(tuple(self.func) + tuple(self.args))

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())

    @property
    def rows(self):
        rows = OrderedSet()
        for arg in self.args:
            if isinstance(arg, Expression):
                rows |= arg.rows
        return rows

    def _to_sql(self, alias_mapping):
        sql = "{func}({params})"
        args = []

        _sql = []
        for arg in self.args:
            if isinstance(arg, Row):
                _sql.append("*")
            elif isinstance(arg, Expression):
                __sql, _args = arg._to_sql(alias_mapping)
                if isinstance(arg, Select):
                    _sql.append("(%s)" % __sql)
                else:
                    _sql.append(__sql)
                args += _args
            else:
                args.append(arg)
                _sql.append('%s')

        params = ', '.join(_sql)
        return (sql.format(func=self.func, params=params), args)


class Unnest(Func):

    def __init__(self, *args):
        """
        Class for the UNNEST SQL function.

        This function is special since it can be used as a table in the FROM clause of
        some queries, therefore we create a Row object for it.
        """
        super(Unnest, self).__init__('unnest', *args)
        # Mimic a row
        self._table = self.func
        self._cols = self.args

    @property
    def rows(self):
        return OrderedSet([self])

    def _to_sql(self, alias_mapping):
        sql, args = super(Unnest, self)._to_sql(alias_mapping)
        sql += " %s" % alias_mapping[self]
        return sql, args


class Now(Func):

    def __init__(self):
        """
        Class for the NOW SQL function.

        It is a bit special since at Odoo we usually use it with `at timezone 'UTC'`.
        """
        super(Now, self).__init__('now')

    def _to_sql(self, alias_mapping):
        sql, args = super(Now, self)._to_sql(alias_mapping)
        sql += " at timezone 'UTC'"

        return (sql, args)


now = Now
unnest = Unnest
avg = partial(Func, 'avg')
count = partial(Func, 'count')
_sum = partial(Func, 'sum')
_max = partial(Func, 'max')
_min = partial(Func, 'min')
coalesce = partial(Func, 'coalesce')
nullif = partial(Func, 'nullif')
concat = partial(Func, 'concat')
exists = partial(Func, 'exists')
_any = partial(Func, 'any')
substr = partial(Func, 'substr')
length = partial(Func, 'length')
