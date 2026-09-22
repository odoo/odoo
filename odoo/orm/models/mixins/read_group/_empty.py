import typing

from .... import decorators as api
from ....parsing import parse_read_group_spec
from .._model_stubs import _ModelStubs


class _ReadGroupEmptyMixin(_ModelStubs):
    __slots__ = ()

    @api.model
    def _read_group_empty_value(self, spec: str) -> typing.Any:
        if spec == "__count":
            return 0
        fname, chain_fnames, func = parse_read_group_spec(spec)
        if func in ("count", "count_distinct"):
            return 0
        if func in ("array_agg", "array_agg_distinct"):
            return []
        field = self._fields[fname]
        if (not func or func == "recordset") and (field.relational or fname == "id"):
            if chain_fnames and field.is_many2one:
                groupby_seq = f"{chain_fnames}:{func}" if func else chain_fnames
                model = self.env[field.comodel_name]
                return model._read_group_empty_value(groupby_seq)
            return (
                self.env[field.comodel_name]
                if field.relational
                else self.env[self._name]
            )
        return False
