# -*- coding: utf-8 -*-
import datetime
from itertools import chain

from .parser import Parser
from .exceptions import QueryFormatError


class Serializer(object):
    def __init__(self, record, query="{*}", many=False):
        self.many = many
        self._record = record
        self._raw_query = query
        super().__init__()

    def get_parsed_restql_query(self):
        parser = Parser(self._raw_query)
        try:
            parsed_restql_query = parser.get_parsed()
            return parsed_restql_query
        except SyntaxError as e:
            msg = "QuerySyntaxError: " + e.msg + " on " + e.text
            raise SyntaxError(msg) from None
        except QueryFormatError as e:
            msg = "QueryFormatError: " + str(e)
            raise QueryFormatError(msg) from None

    @property
    def data(self):
        parsed_restql_query = self.get_parsed_restql_query()
        if self.many:
            return [
                self.serialize(rec, parsed_restql_query)
                for rec
                in self._record
            ]
        return self.serialize(self._record, parsed_restql_query)

    @classmethod
    def build_flat_field(cls, rec, field_name):
        all_fields = rec.fields_get()
        if field_name not in all_fields:
            msg = "'%s' field is not found" % field_name
            raise LookupError(msg)
        field_type = rec.fields_get(field_name).get(field_name).get('type')
        if field_type in ['one2many', 'many2many']:
            return {
                field_name: [record.id for record in rec[field_name]]
            }
        elif field_type in ['many2one']:
            return {field_name: rec[field_name].id}
        elif field_type == 'datetime' and rec[field_name]:
            return {
                field_name: rec[field_name].strftime("%Y-%m-%d-%H-%M")
            }
        elif field_type == 'date' and rec[field_name]:
            return {
                field_name: rec[field_name].strftime("%Y-%m-%d")
            }
        elif field_type == 'time' and rec[field_name]:
            return {
                field_name: rec[field_name].strftime("%H-%M-%S")
            }
        elif field_type == "binary" and isinstance(rec[field_name], bytes) and rec[field_name]:
            return {field_name: rec[field_name].decode("utf-8")}
        else:
            return {field_name: rec[field_name]}

    @classmethod
    def build_nested_field(cls, rec, field_name, nested_parsed_query):
        all_fields = rec.fields_get()
        if field_name not in all_fields:
            msg = "'%s' field is not found" % field_name
            raise LookupError(msg)
        field_type = rec.fields_get(field_name).get(field_name).get('type')
        if field_type in ['one2many', 'many2many']:
            return {
                field_name: [
                    cls.serialize(record, nested_parsed_query)
                    for record
                    in rec[field_name]
                ]
            }
        elif field_type in ['many2one']:
            return {
                field_name: cls.serialize(rec[field_name], nested_parsed_query)
            }
        else:
            # Not a neste field
            msg = "'%s' is not a nested field" % field_name
            raise ValueError(msg)

    @classmethod
    def serialize(cls, rec, parsed_query):
        data = {}

        # NOTE: self.parsed_restql_query["include"] not being empty
        # is not a guarantee that the exclude operator(-) has not been
        # used because the same self.parsed_restql_query["include"]
        # is used to store nested fields when the exclude operator(-) is used
        if parsed_query["exclude"]:
            # Exclude fields from a query
            all_fields = rec.fields_get()
            for field in parsed_query["include"]:
                if field == "*":
                    continue
                for nested_field, nested_parsed_query in field.items():
                    built_nested_field = cls.build_nested_field(
                        rec,
                        nested_field,
                        nested_parsed_query
                    )
                    data.update(built_nested_field)

            flat_fields= set(all_fields).symmetric_difference(set(parsed_query['exclude']))
            for field in flat_fields:
                flat_field = cls.build_flat_field(rec, field)
                data.update(flat_field)

        elif parsed_query["include"]:
            # Here we are sure that self.parsed_restql_query["exclude"]
            # is empty which means the exclude operator(-) is not used,
            # so self.parsed_restql_query["include"] contains only fields
            # to include
            all_fields = rec.fields_get()
            if "*" in parsed_query['include']:
                # Include all fields
                parsed_query['include'] = filter(
                    lambda item: item != "*",
                    parsed_query['include']
                )
                fields = chain(parsed_query['include'], all_fields)
                parsed_query['include'] = list(fields)

            for field in parsed_query["include"]:
                if isinstance(field, dict):
                    for nested_field, nested_parsed_query in field.items():
                        built_nested_field = cls.build_nested_field(
                            rec,
                            nested_field,
                            nested_parsed_query
                        )
                        data.update(built_nested_field)
                else:
                    flat_field = cls.build_flat_field(rec, field)
                    data.update(flat_field)
        else:
            # The query is empty i.e query={}
            # return nothing
            return {}
        return data