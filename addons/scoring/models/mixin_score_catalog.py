from odoo import api, models


class MixinScoreCatalog(models.AbstractModel):
    _name = "mixin.score.catalog"
    _description = "Scored Catalog Mixin"

    # Field carrying the points a record is worth. It answers "did this record
    # contribute anything", which is the right question on create and unlink.
    _score_weight_field = None

    # Fields whose change can move a ceiling or rewrite a breakdown label. The
    # weight alone is not enough: archiving a weighted value, renaming it, or
    # re-homing it under another attribute each move something the score
    # depends on, and none of them touches the weight field. Left empty, the
    # mixin falls back to _score_weight_field, and treats every write as
    # relevant only when neither is set.
    _score_catalog_fields = ()

    def _has_score_weight(self):
        field_name = self._score_weight_field
        if not field_name:
            return bool(self)
        return any(record[field_name] for record in self)

    def _score_catalog_trigger_fields(self):
        """Names of the fields whose change invalidates the score catalog."""
        if self._score_catalog_fields:
            return self._score_catalog_fields
        if self._score_weight_field:
            return (self._score_weight_field,)
        return ()

    def _score_catalog_field_moved(self, record, field_name, value):
        current = record[field_name]
        if self._fields[field_name].type == "many2one":
            current = current.id
        return current != value

    def _score_catalog_changes(self, vals):
        watched = self._score_catalog_trigger_fields()
        if not watched:
            return bool(self)
        changed = [name for name in watched if name in vals]
        if not changed:
            return False
        return any(
            self._score_catalog_field_moved(record, name, vals[name])
            for record in self
            for name in changed
        )

    @api.model
    def _score_catalog_models(self):
        """The catalog models a change to this one moves the ceiling of.

        A value belongs to its attribute's catalog: a dimension names the
        attribute model, and a weight edited on a value is that ceiling moving.
        """
        names = [self._name]
        attribute = self._fields.get("attribute_id")
        if attribute is not None and attribute.comodel_name:
            names.append(attribute.comodel_name)
        return names

    @api.model
    def _score_ceilings(self, domain):
        ceilings = []
        for attribute in self.search(domain):
            if attribute.aggregation_mode == "none":
                continue
            scores = [
                score
                for score in attribute.value_ids.mapped("score_value")
                if score > 0
            ]
            if not scores:
                continue
            summable = (
                attribute.value_type == "multi" and attribute.aggregation_mode == "sum"
            )
            ceilings.append((attribute.id, sum(scores) if summable else max(scores)))
        return {
            "model": self._name,
            "attributes": tuple(ceilings),
            "total": sum(ceiling for _attribute_id, ceiling in ceilings),
        }

    @api.model
    def _score_labels(self, keys):
        """Resolve '<code>:<attribute>:<value|none>' keys into reader-language labels.

        Archived records still label their rows: a row outlives the archive
        until the next refresh drops it, and a key is a worse label than the
        name of the thing it names.
        """
        parsed = {}
        for key in keys:
            _code, attribute_id, value_id = key.split(":")
            parsed[key] = (
                int(attribute_id),
                None if value_id == "none" else int(value_id),
            )
        attributes = self.sudo().with_context(active_test=False)
        values = (
            self.env[self._fields["value_ids"].comodel_name]
            .sudo()
            .with_context(active_test=False)
        )
        attribute_names = {
            record.id: record.name
            for record in attributes.browse({a for a, _v in parsed.values()}).exists()
        }
        value_names = {
            record.id: record.name
            for record in values.browse(
                {v for _a, v in parsed.values() if v is not None}
            ).exists()
        }
        labels = {}
        for key, (attribute_id, value_id) in parsed.items():
            attribute_name = attribute_names.get(attribute_id)
            if attribute_name is None:
                continue
            if value_id is None:
                labels[key] = attribute_name
            elif value_id in value_names:
                labels[key] = f"{attribute_name}: {value_names[value_id]}"
        return labels

    def _notify_score_catalog_changed(self):
        self.env["scorecard"]._notify_catalog_changed(self._score_catalog_models())

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        field_name = self._score_weight_field
        if field_name and any(vals.get(field_name) for vals in vals_list):
            records._notify_score_catalog_changed()
        return records

    def write(self, vals):
        moved = self._score_catalog_changes(vals)
        result = super().write(vals)
        if moved:
            self._notify_score_catalog_changed()
        if "name" in vals:
            self.env["scorecard"]._invalidate_line_labels()
        return result

    def unlink(self):
        weighted = self._has_score_weight()
        result = super().unlink()
        if weighted:
            self._notify_score_catalog_changed()
        return result
