from collections import defaultdict
from datetime import date
from itertools import groupby

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)

_IDENTITY_FIELDS = ("skill_type_id", "skill_id", "skill_level_id")


class MixinHrIndividualSkill(models.AbstractModel):
    _name = "mixin.hr.individual.skill"
    _description = "Skill level"
    _order = "skill_type_id, skill_level_id"
    _rec_name = "skill_id"

    def _linked_field_name(self):
        raise NotImplementedError

    def _get_fields_passive(self):
        return []

    def _can_edit_certification_validity_period(self):
        return True

    def _default_skill_type_id(self):
        if self.env.context.get("certificate_skill", False):
            return self.env["hr.skill.type"]._get_certification_type()
        return self.env["hr.skill.type"].search([], limit=1)

    skill_id = fields.Many2one(
        comodel_name="hr.skill",
        compute="_compute_skill_id",
        store=True,
        readonly=False,
        required=True,
        domain="[('skill_type_id', '=', skill_type_id)]",
        ondelete="cascade",
    )
    skill_level_id = fields.Many2one(
        comodel_name="hr.skill.level",
        compute="_compute_skill_level_id",
        store=True,
        readonly=False,
        required=True,
        domain="[('skill_type_id', '=', skill_type_id)]",
        ondelete="cascade",
    )
    skill_type_id = fields.Many2one(
        comodel_name="hr.skill.type",
        default=_default_skill_type_id,
        required=True,
        ondelete="cascade",
    )
    level_progress = fields.Integer(related="skill_level_id.level_progress")
    color = fields.Integer(related="skill_type_id.color")
    valid_from = fields.Date(
        string="Validity Start",
        default=fields.Date.today,
        required=True,
    )
    valid_to = fields.Date(string="Validity Stop")
    levels_count = fields.Integer(related="skill_type_id.levels_count")
    certification_skill_type_count = fields.Integer(
        export_string_translation=False,
        compute="_compute_certification_skill_type_count",
    )
    is_certification = fields.Boolean(
        related="skill_type_id.is_certification",
        export_string_translation=False,
    )
    display_warning_message = fields.Boolean(
        export_string_translation=False,
        compute="_compute_display_warning_message",
    )

    @api.model
    def _concrete_individual_skill_models(self):
        registry = self.env.registry
        pending = list(registry[self._name]._inherit_children)
        seen = set()
        concrete = []
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            pending.extend(registry[name]._inherit_children)
            if not registry[name]._abstract:
                concrete.append(self.env[name])
        return concrete

    @api.model
    def _check_library_type_matches_rows(self, library_records, field_name):
        row_models = self._concrete_individual_skill_models()
        if not (row_models and library_records):
            return
        library_records.flush_recordset(["skill_type_id"])
        for model in row_models:
            model.flush_model([field_name, "skill_type_id"])
        self.env.cr.execute(
            SQL(
                "SELECT model, row_type, library_id FROM (%s) AS mismatch LIMIT 1",
                SQL(" UNION ALL ").join(
                    SQL(
                        """
                        SELECT %(model)s AS model, s.skill_type_id AS row_type,
                               library.id AS library_id
                          FROM %(rows)s s
                          JOIN %(library)s library ON library.id = s.%(field)s
                         WHERE library.id = ANY(%(ids)s)
                           AND s.skill_type_id != library.skill_type_id
                        """,
                        model=model._name,
                        rows=SQL.identifier(model._table),
                        library=SQL.identifier(library_records._table),
                        field=SQL.identifier(field_name),
                        ids=library_records.ids,
                    )
                    for model in row_models
                ),
            )
        )
        if mismatch := self.env.cr.fetchone():
            model_name, row_type_id, library_id = mismatch
            record = library_records.browse(library_id)
            raise ValidationError(
                self.env._(
                    "%(record)s is recorded under %(type)s in %(model)s, "
                    "so it cannot move to %(new_type)s.",
                    record=record.name,
                    type=self.env["hr.skill.type"].browse(row_type_id).name,
                    model=self.env[model_name]._description,
                    new_type=record.skill_type_id.name,
                )
            )

    @staticmethod
    def _domain_not_ended(day):
        return Domain("valid_to", "=", False) | Domain("valid_to", ">=", day)

    @classmethod
    def _domain_held(cls, day):
        return Domain("valid_from", "<=", day) & cls._domain_not_ended(day)

    def _domain_current(self, day):
        linked_field = SQL.identifier(self._linked_field_name())
        table = SQL.identifier(self._table)
        return Domain(
            "id",
            "in",
            SQL(
                """
                SELECT s.id
                  FROM %(table)s s
                 WHERE s.valid_to IS NULL
                    OR s.valid_to >= %(day)s
                    OR (
                        %(keep_lapsed)s
                        AND EXISTS (
                            SELECT 1
                              FROM hr_skill skill
                              JOIN hr_skill_type skill_type
                                ON skill_type.id = skill.skill_type_id
                             WHERE skill.id = s.skill_id AND skill_type.is_certification
                        )
                        AND NOT EXISTS (
                            SELECT 1
                              FROM %(table)s o
                             WHERE o.%(linked)s = s.%(linked)s
                               AND o.skill_id = s.skill_id
                               AND (o.valid_to IS NULL OR o.valid_to >= %(day)s)
                        )
                        AND s.valid_to = (
                            SELECT max(o.valid_to)
                              FROM %(table)s o
                             WHERE o.%(linked)s = s.%(linked)s
                               AND o.skill_id = s.skill_id
                        )
                    )
                """,
                table=table,
                linked=linked_field,
                day=day,
                keep_lapsed=self._can_edit_certification_validity_period(),
            ),
        )

    def _held_individual_skills(self, day=None):
        day = day or fields.Date.today()
        return self.filtered(
            lambda row: (
                row.valid_from <= day and (not row.valid_to or row.valid_to >= day)
            )
        )

    def _overlap_vals(self, valid_to=None):
        self.check_singleton()
        return {
            self._linked_field_name(): self[self._linked_field_name()].id,
            "skill_id": self.skill_id.id,
            "id": self.id,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to if valid_to is None else valid_to,
            "skill_level_id": self.skill_level_id.id,
            "is_certification": self.is_certification,
        }

    @api.constrains(
        lambda self: [
            "valid_from",
            "valid_to",
            "skill_id",
            "skill_type_id",
            "skill_level_id",
            self._linked_field_name(),
        ]
    )
    def _check_not_overlapping_regular_skill(self):
        overlapping_dict = self._get_overlapping_individual_skill(
            [skill_ind._overlap_vals() for skill_ind in self]
        )
        if not overlapping_dict:
            return
        errors = [
            self.env._(
                "• %(new_skills)s conflicts with the existing skill/certification %(existing)s from %(valid_from)s to %(valid_to)s",
                new_skills=", ".join(
                    self._describe_individual_skill_vals(ind_skill)
                    for ind_skill in new_ind_skills
                ),
                existing=existing_ind_skill.display_name,
                valid_from=existing_ind_skill.valid_from,
                valid_to=existing_ind_skill.valid_to or self.env._("no end date"),
            )
            for existing_ind_skill, new_ind_skills in overlapping_dict.items()
        ]
        _debug.logic(
            "overlap_refused", model=self._name, colliding=len(overlapping_dict)
        )
        raise ValidationError(
            self.env._(
                "The following skills can't be created as they overlap or exactly match existing skills:\n%(collisions)s",
                collisions="\n".join(errors),
            )
        )

    def _describe_individual_skill_vals(self, vals):
        skill = self.env["hr.skill"].browse(vals.get("skill_id"))
        level = self.env["hr.skill.level"].browse(vals.get("skill_level_id"))
        return self.env._(
            "%(skill)s: %(level)s from %(valid_from)s to %(valid_to)s",
            skill=skill.name,
            level=level.name,
            valid_from=vals.get("valid_from"),
            valid_to=vals.get("valid_to") or self.env._("no end date"),
        )

    def _certification_identity_of(self, stored):
        return (
            stored[self._linked_field_name()].id,
            stored.skill_id.id,
            stored.skill_level_id.id,
            stored.valid_from,
            stored.valid_to,
        )

    @staticmethod
    def _spans_overlap(start, stop, other_start, other_stop):
        return start <= (other_stop or date.max) and other_start <= (stop or date.max)

    def _collides(self, stored, vals, as_certification):
        if as_certification:
            return (stored.skill_level_id.id, stored.valid_from, stored.valid_to) == (
                vals["skill_level_id"],
                vals["valid_from"],
                vals["valid_to"],
            )
        return self._spans_overlap(
            stored.valid_from, stored.valid_to, vals["valid_from"], vals["valid_to"]
        )

    def _get_overlapping_individual_skill(self, vals_list):
        overlapping = defaultdict(list)
        if not vals_list:
            return overlapping
        linked_field = self._linked_field_name()
        can_edit_certification_validity_period = (
            self._can_edit_certification_validity_period()
        )
        stored_rows = self.env[self._name].search(
            Domain(linked_field, "in", list({vals[linked_field] for vals in vals_list}))
            & Domain("skill_id", "in", list({vals["skill_id"] for vals in vals_list}))
        )
        stored_by_key = stored_rows.grouped(
            lambda row: (row[linked_field].id, row.skill_id.id)
        )
        for vals in vals_list:
            as_certification = (
                can_edit_certification_validity_period and vals["is_certification"]
            )
            for stored in stored_by_key.get((vals[linked_field], vals["skill_id"]), ()):
                if stored.id != vals["id"] and self._collides(
                    stored, vals, as_certification
                ):
                    overlapping[stored].append(vals)
        _debug.logic(
            "overlap.checked",
            model=self._name,
            candidates=len(vals_list),
            stored=stored_rows,
            colliding=len(overlapping),
        )
        return overlapping

    @api.constrains("valid_from", "valid_to")
    def _check_date(self):
        errors = [
            self.env._(
                "• %(skill_name)s from %(valid_from)s to %(valid_to)s",
                skill_name=ind_skill.display_name,
                valid_from=ind_skill.valid_from,
                valid_to=ind_skill.valid_to,
            )
            for ind_skill in self
            if ind_skill.valid_to and ind_skill.valid_from > ind_skill.valid_to
        ]
        if errors:
            _debug.logic("date_order_refused", skills=self, bad=len(errors))
            raise ValidationError(
                self.env._(
                    "The following skills have their valid stop date prior to "
                    "their valid start date:\n%(collisions)s",
                    collisions="\n".join(errors),
                )
            )

    @api.constrains("skill_id", "skill_type_id")
    def _check_skill_type(self):
        for record in self:
            if record.skill_id.skill_type_id != record.skill_type_id:
                _debug.logic(
                    "skill_type_mismatch",
                    record=record,
                    skill_type=record.skill_id.skill_type_id,
                    declared=record.skill_type_id,
                )
                raise ValidationError(
                    self.env._(
                        "The skill %(name)s and skill type %(type)s don't match",
                        name=record.skill_id.name,
                        type=record.skill_type_id.name,
                    )
                )

    @api.constrains("skill_type_id", "skill_level_id")
    def _check_skill_level(self):
        for record in self:
            if record.skill_level_id.skill_type_id != record.skill_type_id:
                _debug.logic(
                    "skill_level_mismatch",
                    record=record,
                    level=record.skill_level_id,
                    declared=record.skill_type_id,
                )
                raise ValidationError(
                    self.env._(
                        "The skill level %(level)s is not valid for skill type: %(type)s",
                        level=record.skill_level_id.name,
                        type=record.skill_type_id.name,
                    )
                )

    def _compute_certification_skill_type_count(self):
        self.certification_skill_type_count = self.env["hr.skill.type"].search_count(
            [("is_certification", "=", True)]
        )

    @api.onchange("is_certification")
    def _onchange_is_certification(self):
        self.valid_from = fields.Date.today()
        if not self.is_certification:
            self.valid_to = False

    @api.depends("skill_type_id")
    def _compute_skill_id(self):
        for record in self:
            record.skill_id = record.skill_type_id.skill_ids[:1]

    @api.depends("skill_id", "skill_type_id")
    def _compute_skill_level_id(self):
        for record in self:
            if not record.skill_id:
                record.skill_level_id = False
                continue
            skill_levels = record.skill_type_id.skill_level_ids
            record.skill_level_id = (
                skill_levels.filtered("default_level")[:1] or skill_levels[:1]
            )

    @api.depends("skill_id.name", "skill_level_id.name")
    def _compute_display_name(self):
        for individual_skill in self:
            individual_skill.display_name = f"{individual_skill.skill_id.name}: {individual_skill.skill_level_id.name}"

    @api.depends("valid_from", "valid_to")
    def _compute_display_warning_message(self):
        for individual_skill in self:
            individual_skill.display_warning_message = bool(
                individual_skill.valid_to
                and individual_skill.valid_from
                and individual_skill.valid_to < individual_skill.valid_from
            )

    def _current_individual_skills(self):
        today = fields.Date.today()
        keep_latest_lapsed_certification = (
            self._can_edit_certification_validity_period()
        )
        linked_field = self._linked_field_name()
        kept_ids = set()
        for (_owner, skill), rows in self.grouped(
            lambda row: (row[linked_field], row.skill_id)
        ).items():
            not_ended = rows.filtered(
                lambda row: not row.valid_to or row.valid_to >= today
            )
            if not_ended or not (
                keep_latest_lapsed_certification
                and skill.skill_type_id.is_certification
            ):
                kept_ids.update(not_ended.ids)
                continue
            by_valid_to = rows.grouped("valid_to")
            kept_ids.update(by_valid_to[max(by_valid_to)].ids)
        _debug.logic("current_skills", model=self._name, rows=self, kept=len(kept_ids))
        return self.filtered(lambda row: row.id in kept_ids)

    def _expire_individual_skills(self):
        yesterday = fields.Date.today() - relativedelta(days=1)
        to_remove = self.filtered(
            lambda skill: (
                skill.valid_from >= yesterday
                or (skill.valid_to and skill.valid_to <= yesterday)
            )
        )
        to_archive = self - to_remove
        if to_archive:
            overlapping_dict = self._get_overlapping_individual_skill(
                [skill._overlap_vals(valid_to=yesterday) for skill in to_archive]
            )
            overlapped_ids = {
                new_skill["id"]
                for new_skills in overlapping_dict.values()
                for new_skill in new_skills
            }
            changed_to_remove = to_archive.filtered(
                lambda ind_skill: ind_skill.id in overlapped_ids
            )
            to_archive -= changed_to_remove
            to_remove += changed_to_remove
        _debug.pipeline(
            "expire",
            model=self._name,
            deleted=to_remove,
            archived=to_archive,
            until=str(yesterday),
        )
        return [Command.delete(skill.id) for skill in to_remove] + [
            Command.update(skill.id, {"valid_to": yesterday}) for skill in to_archive
        ]

    def _search_live_skills_for(self, vals_list):
        linked_field = self._linked_field_name()
        linked_ids = {
            vals[linked_field] for vals in vals_list if vals.get(linked_field)
        }
        if not linked_ids:
            return self.env[self._name]
        live_domain = self._domain_not_ended(fields.Date.today())
        if self._can_edit_certification_validity_period():
            live_domain |= Domain("is_certification", "=", True)
        return self.env[self._name].search(
            Domain(linked_field, "in", list(linked_ids))
            & Domain("skill_id", "in", list({vals["skill_id"] for vals in vals_list}))
            & live_domain
        )

    def _create_individual_skills(self, vals_list, ended=None):
        can_edit_certification_validity_period = (
            self._can_edit_certification_validity_period()
        )
        linked_field = self._linked_field_name()
        vals_list = [
            vals
            if vals.get("skill_type_id")
            else {
                **vals,
                "skill_type_id": self.env["hr.skill"]
                .browse(vals["skill_id"])
                .skill_type_id.id,
            }
            for vals in vals_list
        ]

        seen_skills = set()
        skills_to_archive = self.env[self._name]
        vals_to_return = []

        existing_skills = self._search_live_skills_for(vals_list)
        if ended:
            existing_skills -= ended
        existing_skills_grouped = existing_skills.grouped(
            lambda skill: (skill[linked_field].id, skill.skill_id.id)
        )

        certification_identities = set()
        certification_types = set()
        if can_edit_certification_validity_period:
            certification_identities = {
                self._certification_identity_of(cert)
                for cert in existing_skills.filtered("is_certification")
            }
            certification_types = set(
                self.env["hr.skill.type"]
                .browse([vals["skill_type_id"] for vals in vals_list])
                .filtered("is_certification")
                .ids
            )
        for vals in vals_list:
            linked_id = vals.get(linked_field, False)
            skill_id = vals["skill_id"]
            valid_from = fields.Date.from_string(vals.get("valid_from"))
            valid_to = fields.Date.from_string(vals.get("valid_to")) or False

            skill_key = (linked_id, skill_id, valid_from, valid_to)
            if skill_key in seen_skills:
                continue
            seen_skills.add(skill_key)

            if vals["skill_type_id"] in certification_types:
                identity = (
                    linked_id,
                    skill_id,
                    vals["skill_level_id"],
                    valid_from,
                    valid_to,
                )
                if linked_id and identity in certification_identities:
                    continue
            elif linked_id:
                skills_to_archive |= existing_skills_grouped.get(
                    (linked_id, skill_id), self.env[self._name]
                )

            vals_to_return.append(vals)

        _debug.logic(
            "create.resolved",
            model=self._name,
            requested=len(vals_list),
            created=len(vals_to_return),
            superseded=skills_to_archive,
            already_ended=ended,
        )
        return skills_to_archive._expire_individual_skills() + [
            Command.create(new_create_val) for new_create_val in vals_to_return
        ]

    def _passive_field_value(self, field_name):
        field_type = self._fields[field_name].type
        if field_type == "many2one":
            return self[field_name].id
        if field_type in {"many2many", "one2many"}:
            return self[field_name].ids
        return self[field_name]

    def _prepare_individual_skill_updates(self, vals_by_id):
        linked_field = self._linked_field_name()
        plain_updates = []
        superseded = self.env[self._name]
        successor_vals = []
        for row in self:
            vals = vals_by_id[row.id]
            if vals.get(linked_field, row[linked_field].id) != row[linked_field].id:
                _debug.logic("skill_reparent_refused", skill=row)
                raise ValidationError(
                    self.env._(
                        "The skill %(skill)s cannot be moved to another record.",
                        skill=row.display_name,
                    )
                )
            if not any(field in vals for field in _IDENTITY_FIELDS):
                plain_updates.append(Command.update(row.id, vals))
                continue
            superseded |= row
            new_vals = {
                field: vals.get(field, row._passive_field_value(field))
                for field in (
                    *_IDENTITY_FIELDS,
                    linked_field,
                    *self._get_fields_passive(),
                )
            }
            is_certification = (
                self.env["hr.skill.type"]
                .browse(new_vals["skill_type_id"])
                .is_certification
            )
            new_vals["valid_from"] = vals.get(
                "valid_from",
                row.valid_from if is_certification else fields.Date.today(),
            )
            new_vals["valid_to"] = vals.get(
                "valid_to", row.valid_to if is_certification else False
            )
            successor_vals.append(new_vals)
        _debug.pipeline(
            "updates_prepared",
            model=self._name,
            plain=len(plain_updates),
            superseded=superseded,
            successors=len(successor_vals),
        )
        return plain_updates, superseded, successor_vals

    @staticmethod
    def _referenced_row_ids(commands):
        referenced = set()
        for command in commands:
            if command[0] == Command.SET:
                referenced.update(command[2])
            elif command[0] not in (Command.CREATE, Command.CLEAR):
                referenced.add(command[1])
        return referenced

    def _raise_foreign_rows(self):
        _debug.logic("foreign_rows_refused", skills=self)
        raise ValidationError(
            self.env._(
                "These skills belong to another record: %(skills)s",
                skills=", ".join(self.mapped("display_name")),
            )
        )

    def _get_transformed_commands(self, commands, individual):
        if not commands:
            return []
        if individual:
            individual.check_singleton()
        return self._transform_commands_by_individual({individual: commands})

    def _transform_commands_by_individual(self, commands_by_individual):
        skill_model = self.env[self._name]
        linked_field = self._linked_field_name()
        vals_by_id = defaultdict(dict)
        created_values = []
        ended_ids = set()
        kept_ids = set()
        clearing_ids = []
        referenced_by_individual = {}
        for individual, commands in commands_by_individual.items():
            for command in commands:
                match command[0]:
                    case Command.CREATE:
                        individual_command = dict(command[2])
                        if individual:
                            individual_command[linked_field] = individual.id
                        else:
                            # The owner is being created: copy_data hands over the
                            # lines with the *old* owner's id, which the ORM will
                            # overwrite. Resolving collisions against it would
                            # close the skills of the record being copied.
                            individual_command.pop(linked_field, None)
                        created_values.append(individual_command)
                    case Command.UPDATE:
                        vals_by_id[command[1]].update(command[2])
                    case Command.DELETE | Command.UNLINK:
                        ended_ids.add(command[1])
                    case Command.LINK:
                        kept_ids.add(command[1])
                    case Command.CLEAR:
                        clearing_ids.append(individual.id)
                    case Command.SET:
                        clearing_ids.append(individual.id)
                        kept_ids.update(command[2])
                    case _:
                        raise NotImplementedError(
                            f"unsupported x2many command {command[0]!r}"
                        )
            referenced_by_individual[individual] = self._referenced_row_ids(commands)
        referenced = skill_model.browse(
            list(set().union(*referenced_by_individual.values()))
        )
        owner_of_row = {row.id: row[linked_field] for row in referenced}
        foreign = referenced.browse(
            [
                row_id
                for individual, row_ids in referenced_by_individual.items()
                for row_id in row_ids
                if owner_of_row[row_id] != individual
            ]
        )
        if foreign:
            foreign._raise_foreign_rows()
        if clearing_ids := [owner_id for owner_id in clearing_ids if owner_id]:
            ended_ids.update(
                skill_model.search(
                    Domain(linked_field, "in", clearing_ids)
                    & self._domain_not_ended(fields.Date.today())
                ).ids
            )
            ended_ids -= kept_ids
        ended = skill_model.browse(list(ended_ids))
        plain_updates, superseded, successor_vals = skill_model.browse(
            [row_id for row_id in vals_by_id if row_id not in ended_ids]
        )._prepare_individual_skill_updates(vals_by_id)
        ended |= superseded
        _debug.logic(
            "commands.transformed",
            model=self._name,
            individuals=len(commands_by_individual),
            received=sum(map(len, commands_by_individual.values())),
            ended=ended,
            plain_updates=len(plain_updates),
            creates=len(created_values) + len(successor_vals),
        )
        return (
            ended._expire_individual_skills()
            + plain_updates
            + skill_model._create_individual_skills(
                created_values + successor_vals, ended=ended
            )
        )

    def _apply_individual_skill_commands(self, commands):
        skill_model = self.env[self._name]
        _debug.pipeline("commands_applied", model=self._name, commands=len(commands))
        skill_model.browse(
            [command[1] for command in commands if command[0] == Command.DELETE]
        ).unlink()
        for _command_type, run in groupby(
            (command for command in commands if command[0] != Command.DELETE),
            key=lambda command: (
                command[0],
                command[0] == Command.UPDATE and repr(sorted(command[2].items())),
            ),
        ):
            run = list(run)
            if run[0][0] == Command.UPDATE:
                skill_model.browse([command[1] for command in run]).write(run[0][2])
            else:
                skill_model.create([command[2] for command in run])

    def _commands_by_individual(self, commands, individuals):
        linked_field = self._linked_field_name()
        referenced = self.browse(list(self._referenced_row_ids(commands)))
        owner_of_row = {row.id: row[linked_field] for row in referenced}
        foreign = referenced.filtered(
            lambda row: owner_of_row[row.id] not in individuals
        )
        if foreign:
            foreign._raise_foreign_rows()
        routed = {}
        _debug.logic(
            "commands_routed",
            model=self._name,
            individuals=individuals,
            referenced=referenced,
        )
        for individual in individuals:
            result = []
            for command in commands:
                if command[0] in (Command.CREATE, Command.CLEAR):
                    result.append(command)
                elif command[0] == Command.SET:
                    result.append(
                        Command.set(
                            [
                                row_id
                                for row_id in command[2]
                                if owner_of_row[row_id] == individual
                            ]
                        )
                    )
                elif owner_of_row[command[1]] == individual:
                    result.append(command)
            if result:
                routed[individual] = result
        return routed
