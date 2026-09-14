import logging
import re
from collections import defaultdict

from odoo import models
from odoo.fields import Domain
from odoo.libs.sql import escape_psql
from odoo.tools import SQL, Query

from odoo.addons.website.tools import similarity_score, text_from_html

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = "website"

    def _search_get_details(self, search_type, order, options):
        result = []
        if search_type in ["pages", "all"]:
            result.append(
                self.env["website.page"]._search_get_detail(self, order, options)
            )
        return result

    def _search_with_fuzzy(self, search_type, search, limit, order, options):
        fuzzy_term = False
        search_details = self._search_get_details(search_type, order, options)
        if search and options.get("allowFuzzy", True):
            fuzzy_term = self._search_find_fuzzy_term(search_details, search)
            if fuzzy_term:
                count, results = self._search_exact(
                    search_details, fuzzy_term, limit, order
                )
                if fuzzy_term.lower() == search.lower():
                    fuzzy_term = False
            else:
                count, results = self._search_exact(
                    search_details, search, limit, order
                )
        else:
            count, results = self._search_exact(search_details, search, limit, order)
        return count, results, fuzzy_term

    def _search_exact(self, search_details, search, limit, order):
        all_results = []
        total_count = 0
        for search_detail in search_details:
            model = self.env[search_detail["model"]]
            results, count = model._search_fetch(search_detail, search, limit, order)
            search_detail["results"] = results
            total_count += count
            search_detail["count"] = count
            all_results.append(search_detail)
        return total_count, all_results

    def _search_render_results(self, search_details, limit):
        for search_detail in search_details:
            fields = search_detail["fetch_fields"]
            results = search_detail["results"]
            icon = search_detail["icon"]
            mapping = search_detail["mapping"]
            results_data = results._search_render_results(fields, mapping, icon, limit)
            search_detail["results_data"] = results_data
        return search_details

    def _search_find_fuzzy_term(
        self, search_details, search, limit=1000, word_list=None
    ):
        if (
            len(search) < 4
            or " " in search
            or len(re.findall(r"\d", search)) / len(search) >= 0.8
        ):
            return search
        search = search.lower()
        words = set()
        best_score = 0
        best_word = None
        enumerate_words = (
            self._trigram_enumerate_words
            if self.env.registry.has_trigram
            else self._basic_enumerate_words
        )
        for word in word_list or enumerate_words(search_details, search, limit):
            if search in word:
                return search
            if word[0] == search[0] and word not in words:
                similarity = similarity_score(search, word)
                if similarity > best_score:
                    best_score = similarity
                    best_word = word
                words.add(word)
        return best_word

    def _search_get_indirect_fields(self, fields, model):
        indirect_fields = {}
        for field in fields:
            field_parts = field.split(".")
            if len(field_parts) != 2:
                continue
            direct, indirect = field_parts
            if direct not in model._fields:
                continue
            direct_field = model._fields[direct]
            comodel_name = direct_field.comodel_name
            if comodel_name not in self.env:
                continue
            comodel_fields = self.env[comodel_name]._fields
            cofield = None
            if hasattr(direct_field, "_description_relation_field"):
                cofield = direct_field._description_relation_field
                if cofield not in comodel_fields:
                    continue
            if indirect in comodel_fields:
                indirect_fields[field] = {
                    "direct": direct,
                    "indirect": indirect,
                    "comodel": self.env[comodel_name],
                    "cofield": cofield,
                }
        return indirect_fields

    def _get_trigram_similarity_query(
        self,
        model,
        fields,
        search,
        id_column,
        rel_table="",
        rel_joinkey="",
        relation_field=None,
        domain=None,
    ):
        subquery = (
            model._search(domain)
            if domain is not None
            else Query(self.env.cr, model._table, model._table_query)
        )
        unaccent = self.env.registry.unaccent
        similarity = SQL(
            "GREATEST(%(similarities)s) as similarity",
            similarities=SQL(", ").join(
                SQL(
                    "word_similarity(%(search)s, %(field)s)",
                    search=unaccent(SQL("%s", search)),
                    field=unaccent(model._field_to_sql(model._table, field, subquery)),
                )
                for field in fields
            ),
        )
        where_clauses = []
        for field_name in fields:
            field = model._fields[field_name]
            if field.translate:
                alias = model._table
                if field.related and not field.store:
                    _, field, alias = model._traverse_related_sql(
                        model._table, field, subquery
                    )
                where_clauses.append(
                    SQL(
                        "(%(search)s <%% %(jsonb_path)s AND %(search)s <%% (%(field)s))",
                        search=unaccent(SQL("%s", search)),
                        jsonb_path=unaccent(
                            SQL(
                                "jsonb_path_query_array(%s, '$.*')::text",
                                SQL.identifier(alias, field.name),
                            )
                        ),
                        field=unaccent(
                            model._field_to_sql(model._table, field_name, subquery)
                        ),
                    )
                )
            else:
                where_clauses.append(
                    SQL(
                        "%(search)s <%% %(field)s",
                        search=unaccent(SQL("%s", search)),
                        field=unaccent(
                            model._field_to_sql(model._table, field_name, subquery)
                        ),
                    )
                )
        subquery.add_where(SQL(" OR ").join(where_clauses))
        tbl_alias = model._table
        if rel_table:
            rel_alias = subquery.get_table_alias(rel_table, rel_joinkey)
            subquery.add_join(
                "JOIN",
                rel_alias,
                rel_table,
                SQL(
                    "%s = %s",
                    SQL(
                        "%s",
                        SQL.identifier(rel_alias, rel_joinkey),
                        to_flush=relation_field,
                    ),
                    SQL.identifier(model._table, "id"),
                ),
            )
            tbl_alias = rel_alias
        return subquery.select(
            SQL(
                "%s as id",
                SQL.identifier(tbl_alias, id_column),
                to_flush=model._fields.get(id_column) if not rel_table else None,
            ),
            similarity,
        )

    def _trigram_enumerate_words(self, search_details, search, limit):
        match_pattern = r"[\w./-]{%s,}" % min(4, len(search) - 3)
        self.env.cr.execute("SET LOCAL pg_trgm.word_similarity_threshold to 0.3;")
        for search_detail in search_details:
            model_name, fields = search_detail["model"], search_detail["search_fields"]
            model = self.env[model_name]
            if search_detail.get("requires_sudo"):
                model = model.sudo()
            domain = Domain.AND(search_detail["base_domain"])
            direct_fields = set(fields).intersection(model._fields)
            indirect_fields = self._search_get_indirect_fields(fields, model)
            fields_by_relation = defaultdict(set)
            for indirect_field in indirect_fields.values():
                fields_by_relation[indirect_field["direct"]].add(
                    indirect_field["indirect"]
                )
            subqueries = (
                [self._get_trigram_similarity_query(model, direct_fields, search, "id")]
                if direct_fields
                else []
            )
            for relation_name, relation_fields in fields_by_relation.items():
                direct_field = model._fields[relation_name]
                comodel = model.env[direct_field.comodel_name]
                relation_domain = None
                if direct_field.type in ("one2many", "many2many"):
                    comodel = comodel.with_context(**direct_field.context)
                    relation_domain = direct_field.get_comodel_domain(model)
                id_column = rel_table = rel_joinkey = ""
                if direct_field.type == "one2many":
                    id_column = direct_field._description_relation_field
                elif direct_field.type == "many2many":
                    id_column = direct_field.column1
                    rel_table = direct_field.relation
                    rel_joinkey = direct_field.column2
                elif direct_field.type == "many2one" and direct_field.store:
                    id_column = "id"
                    rel_table = model._table
                    rel_joinkey = direct_field.name
                else:
                    continue
                subqueries.append(
                    self._get_trigram_similarity_query(
                        comodel,
                        relation_fields,
                        search,
                        id_column,
                        rel_table,
                        rel_joinkey,
                        direct_field,
                        relation_domain,
                    )
                )
            if not subqueries:
                continue
            eligible = model._search(domain)
            query = SQL(
                """
                SELECT id,
                    MAX(similarity) as _best_similarity
                FROM (%s) sub
                WHERE id IN %s
                GROUP BY id
                ORDER BY _best_similarity DESC, id
                LIMIT %s
            """,
                SQL("\nUNION ALL\n").join(subqueries),
                eligible.subselect(),
                limit,
            )
            ids = {row[0] for row in self.env.execute_query(query)}
            _logger.debug(
                "Fuzzy candidates model=%s fields=%s count=%s limit=%s",
                model_name,
                fields,
                len(ids),
                limit,
            )
            domain = Domain.AND([domain, Domain([("id", "in", list(ids))])])
            records = (
                model.search_read(domain, direct_fields, limit=limit)  # noqa: E8507 - one query per searched model
                if direct_fields
                else []
            )
            for record in records:
                for value in record.values():
                    if isinstance(value, str):
                        value = value.lower()
                        yield from re.findall(match_pattern, value)
            if indirect_fields:
                records = model.search(domain, limit=limit)
                for indirect_field in indirect_fields:
                    for value in records.mapped(indirect_field):
                        if isinstance(value, str):
                            value = value.lower()
                            yield from re.findall(match_pattern, value)

    def _basic_enumerate_words(self, search_details, search, limit):
        match_pattern = r"[\w./-]{%s,}" % min(4, len(search) - 3)
        first = escape_psql(search[0])
        for search_detail in search_details:
            model_name, fields = search_detail["model"], search_detail["search_fields"]
            model = self.env[model_name]
            if search_detail.get("requires_sudo"):
                model = model.sudo()
            domain = Domain.AND(search_detail["base_domain"])
            direct_fields = set(fields).intersection(model._fields)
            indirect_fields = self._search_get_indirect_fields(fields, model)
            fields = direct_fields.union(indirect_fields)
            fields_domain = Domain.OR(
                Domain(field, "=ilike", pattern)
                for field in fields
                for pattern in (
                    "%s%%" % first,
                    "%% %s%%" % first,
                    "%%>%s%%" % first,
                )
            )
            domain &= fields_domain
            perf_limit = 1000
            records = (
                model.search_read(domain, direct_fields, limit=perf_limit)  # noqa: E8507 - one query per searched model
                if direct_fields
                else []
            )
            if len(records) == perf_limit:
                exact_records, _count = model._search_fetch(
                    search_detail, search, 1, None
                )
                if exact_records:
                    yield search
            for record in records:
                for field, value in record.items():
                    if isinstance(value, str):
                        value = value.lower()
                        if field == "arch_db":
                            value = text_from_html(value)
                        for word in re.findall(match_pattern, value):
                            if word[0] == search[0]:
                                yield word.lower()
            if indirect_fields:
                records = model.search(domain, limit=limit)
                for indirect_field in indirect_fields:
                    for value in records.mapped(indirect_field):
                        if isinstance(value, str):
                            value = value.lower()
                            yield from re.findall(match_pattern, value)
