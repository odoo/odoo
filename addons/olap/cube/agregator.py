import sqlalchemy

agregator = {}
agregator['sum'] = sqlalchemy.func.sum
agregator['count'] = sqlalchemy.func.count
agregator['avg'] = sqlalchemy.func.avg
agregator['min'] = sqlalchemy.func.min
agregator['max'] = sqlalchemy.func.max

