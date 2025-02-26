from odoo.tools.sql import SQL, SQLable
from odoo.tools.query import Query, IdentifierBuilder
from .domains import Domain


class QueryBuilder(SQLable):
    def __init__(self, model):
        self.env = model.env
        self.model = model
        self.query = Query(model.env, model._table, model._table_sql)
        self.domain = Domain([])
        self.select : list[str | IdentifierBuilder | tuple[str | IdentifierBuilder, str]] = [self.id]

    def __getattr__(self, name: str, /) -> IdentifierBuilder:
        return self.query.get.__getattr__(name)

    def to_sql(self) -> SQL:
        domain = self.domain._optimize(self.model)
        if not domain.is_true():
            self.query.add_where(domain._to_sql(self.model, self.model._table, self.query))
        return self.query.select(*(
            SQL("%s AS %s", s[0], SQL.identifier(s[1])) if isinstance(s, tuple | list) else s
            for s in self.select
        ))
