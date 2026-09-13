from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain

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

    @staticmethod
    def _validity_domain(day):
        return Domain.OR(
            [Domain("valid_to", "=", False), Domain("valid_to", ">=", day)]
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

    def _certification_identity(
        self, linked_id, skill_id, level_id, valid_from, valid_to
    ):
        return (
            linked_id,
            skill_id,
            level_id,
            fields.Date.from_string(valid_from),
            fields.Date.from_string(valid_to),
        )

    def _certification_identity_of(self, stored):
        return self._certification_identity(
            stored[self._linked_field_name()].id,
            stored.skill_id.id,
            stored.skill_level_id.id,
            stored.valid_from,
            stored.valid_to,
        )

    def _certification_identity_of_vals(self, vals):
        return self._certification_identity(
            vals[self._linked_field_name()],
            vals["skill_id"],
            vals["skill_level_id"],
            vals["valid_from"],
            vals["valid_to"],
        )

    def _covers_date(self, individual_skill, day):
        return (
            bool(day)
            and individual_skill.valid_from <= day
            and (not individual_skill.valid_to or individual_skill.valid_to >= day)
        )

    def _get_domain_matching_individual_skill(self, vals, as_certification):
        linked_field = self._linked_field_name()
        domain = Domain.AND(
            [
                Domain(linked_field, "=", vals[linked_field]),
                Domain("skill_id", "=", vals["skill_id"]),
                Domain("id", "!=", vals["id"]),
            ]
        )
        if as_certification:
            return Domain.AND(
                [
                    domain,
                    Domain("skill_level_id", "=", vals["skill_level_id"]),
                    Domain("valid_from", "=", vals["valid_from"]),
                    Domain("valid_to", "=", vals["valid_to"]),
                ]
            )
        return Domain.AND(
            [
                domain,
                Domain.OR(
                    [
                        self._covering_date_domain(vals["valid_from"]),
                        self._covering_date_domain(vals["valid_to"]),
                    ]
                ),
            ]
        )

    def _covering_date_domain(self, day):
        return Domain.AND([Domain("valid_from", "<=", day), self._validity_domain(day)])

    def _get_overlapping_individual_skill(self, vals_list):
        can_edit_certification_validity_period = (
            self._can_edit_certification_validity_period()
        )
        linked_field = self._linked_field_name()
        matching_skill_domain = Domain.FALSE
        overlapping_dict = defaultdict(list)
        certification_dict = defaultdict(list)
        regular_dict = defaultdict(list)

        for vals in vals_list:
            as_certification = (
                can_edit_certification_validity_period and vals["is_certification"]
            )
            matching_skill_domain = Domain.OR(
                [
                    matching_skill_domain,
                    self._get_domain_matching_individual_skill(vals, as_certification),
                ]
            )
            if as_certification:
                certification_dict[self._certification_identity_of_vals(vals)].append(
                    vals
                )
            else:
                regular_dict[(vals[linked_field], vals["skill_id"])].append(vals)

        for stored in self.env[self._name].search(matching_skill_domain):
            if can_edit_certification_validity_period and stored.is_certification:
                same_identity = certification_dict.get(
                    self._certification_identity_of(stored), []
                )
                if same_identity:
                    overlapping_dict[stored].extend(same_identity)
                continue
            for vals in regular_dict.get(
                (stored[linked_field].id, stored.skill_id.id), []
            ):
                if self._covers_date(stored, vals["valid_from"]) or self._covers_date(
                    stored, vals["valid_to"]
                ):
                    overlapping_dict[stored].append(vals)
        return overlapping_dict

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
            if record.skill_id not in record.skill_type_id.skill_ids:
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
            if record.skill_level_id not in record.skill_type_id.skill_level_ids:
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

    @api.depends("skill_id", "skill_level_id")
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
        """The rows still held today, in ``self``'s order.

        A skill is held while its validity covers today. A certification whose
        every row has lapsed is still reported through its latest rows, so a
        holder keeps seeing what expired and when -- but only on models that
        let the user set a validity period; elsewhere a lapsed row is history.
        """
        today = fields.Date.today()
        keep_latest_lapsed_certification = (
            self._can_edit_certification_validity_period()
        )
        linked_field = self._linked_field_name()
        kept_ids = set()
        for (_owner, skill), rows in self.grouped(
            lambda row: (row[linked_field], row.skill_id)
        ).items():
            valid = rows.filtered(lambda row: not row.valid_to or row.valid_to >= today)
            if valid or not (
                keep_latest_lapsed_certification
                and skill.skill_type_id.is_certification
            ):
                kept_ids.update(valid.ids)
                continue
            by_valid_to = rows.grouped("valid_to")
            kept_ids.update(by_valid_to[max(by_valid_to)].ids)
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
        return [Command.delete(skill.id) for skill in to_remove] + [
            Command.update(skill.id, {"valid_to": yesterday}) for skill in to_archive
        ]

    def _search_live_skills_for(self, vals_list, linked_ids_of):
        """Stored skills that the pending values could collide with.

        "Live" means still valid, plus every certification when the model lets
        the user set a validity period, because two certifications differing only
        in their dates are allowed to coexist and both have to be seen.
        """
        validity_domain = self._validity_domain(fields.Date.today())
        if self._can_edit_certification_validity_period():
            validity_domain = Domain.OR(
                [validity_domain, Domain("is_certification", "=", True)]
            )
        linked_field = self._linked_field_name()
        return self.env[self._name].search(
            Domain.AND(
                [
                    Domain.OR(
                        [
                            Domain.AND(
                                [
                                    Domain(linked_field, "in", linked_ids_of(vals)),
                                    Domain(
                                        "skill_id", "=", vals.get("skill_id", False)
                                    ),
                                ]
                            )
                            for vals in vals_list
                        ]
                    ),
                    validity_domain,
                ]
            )
        )

    def _create_individual_skills(self, vals_list, individuals=None, ended=None):
        """``ended`` names rows another command in the same batch already closes,
        so a CREATE that supersedes one of them does not close it a second time."""
        can_edit_certification_validity_period = (
            self._can_edit_certification_validity_period()
        )
        linked_field = self._linked_field_name()
        replay_ids = individuals.ids if individuals else []

        def linked_ids_of(vals):
            explicit = vals.get(linked_field, False)
            return [explicit] if explicit else replay_ids or [False]

        seen_skills = set()
        skills_to_archive = self.env[self._name]
        vals_to_return = []

        existing_skills = self._search_live_skills_for(vals_list, linked_ids_of)
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
            skill_id = vals["skill_id"]
            skill_level_id = vals["skill_level_id"]
            valid_from = fields.Date.from_string(vals.get("valid_from"))
            valid_to = fields.Date.from_string(vals.get("valid_to"))

            skill_key = (vals.get(linked_field, False), skill_id, valid_from, valid_to)
            if skill_key in seen_skills:
                continue
            seen_skills.add(skill_key)

            if vals["skill_type_id"] in certification_types:
                if all(
                    (linked_id, skill_id, skill_level_id, valid_from, valid_to)
                    in certification_identities
                    for linked_id in linked_ids_of(vals)
                ):
                    continue
            else:
                for linked_id in linked_ids_of(vals):
                    skills_to_archive += existing_skills_grouped.get(
                        (linked_id, skill_id), self.env[self._name]
                    )

            vals_to_return.append(vals)

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

    def _write_individual_skills(self, commands):
        linked_field = self._linked_field_name()
        identity_fields = (*_IDENTITY_FIELDS, linked_field)
        self_dict = self.grouped("id")
        result_command = []
        create_vals = []
        remove_from_expire = self.env[self._name]

        for command in commands:
            ind_skill = self_dict.get(command[1])
            vals = command[2]
            if not any(key in vals for key in identity_fields):
                result_command.append(Command.update(ind_skill.id, vals))
                remove_from_expire += ind_skill
                continue

            new_vals = {
                field: vals.get(field, ind_skill._passive_field_value(field))
                for field in (*identity_fields, *self._get_fields_passive())
            }
            is_certification = (
                self.env["hr.skill.type"]
                .browse(new_vals["skill_type_id"])
                .is_certification
            )
            new_vals["valid_from"] = vals.get(
                "valid_from",
                ind_skill.valid_from if is_certification else fields.Date.today(),
            )
            new_vals["valid_to"] = vals.get(
                "valid_to", ind_skill.valid_to if is_certification else False
            )
            create_vals.append(new_vals)
        return (
            result_command
            + (self - remove_from_expire)._expire_individual_skills()
            + self.env[self._name]._create_individual_skills(create_vals)
        )

    def _get_transformed_commands(self, commands, individuals):
        """Translate the commands the client sends for the *current* skill list
        into the commands the stored one2many needs, versioning instead of
        overwriting.

        Only the one2many command shapes are meaningful here. LINK and SET are
        accepted for rows the individuals already own (a round trip of what the
        client was shown) and refused otherwise, because a row cannot move to
        another owner without rewriting its history.
        """
        if not commands:
            return None
        linked_field = self._linked_field_name()
        updated_commands = []
        created_values = []
        unlinked_ids = set()
        linked_ids = set()
        clear = False
        for command in commands:
            match command[0]:
                case Command.CREATE:
                    individual_command = dict(command[2])
                    if len(individuals) == 1:
                        individual_command[linked_field] = individuals.id
                    elif not individuals:
                        # The owner is being created: copy_data hands over the
                        # lines with the *old* owner's id, which the ORM will
                        # overwrite. Resolving collisions against it would
                        # close the skills of the record being copied.
                        individual_command.pop(linked_field, None)
                    created_values.append(individual_command)
                case Command.UPDATE:
                    updated_commands.append(command)
                case Command.DELETE | Command.UNLINK:
                    unlinked_ids.add(command[1])
                case Command.LINK:
                    linked_ids.add(command[1])
                case Command.CLEAR:
                    clear = True
                case Command.SET:
                    clear = True
                    linked_ids.update(command[2])
                case _:
                    raise NotImplementedError(
                        f"unsupported x2many command {command[0]!r}"
                    )
        if clear:
            unlinked_ids.update(
                self.env[self._name]
                .search(
                    Domain.AND(
                        [
                            Domain(linked_field, "in", individuals.ids),
                            self._validity_domain(fields.Date.today()),
                        ]
                    )
                )
                .ids
            )
            unlinked_ids -= linked_ids
        foreign = (
            self.env[self._name]
            .browse(list(linked_ids))
            .filtered(lambda row: row[linked_field] not in individuals)
        )
        if foreign:
            raise NotImplementedError(
                f"{self._name} rows {foreign.ids} belong to another record and "
                "cannot be linked"
            )
        updated_commands = [
            command for command in updated_commands if command[1] not in unlinked_ids
        ]
        updated_ids = [command[1] for command in updated_commands]
        unlinked = self.env[self._name].browse(list(unlinked_ids))
        unlinked_commands = unlinked._expire_individual_skills()
        updated_commands = (
            self.env[self._name]
            .browse(updated_ids)
            ._write_individual_skills(updated_commands)
        )
        created_commands = self.env[self._name]._create_individual_skills(
            created_values, individuals, ended=unlinked
        )
        return unlinked_commands + updated_commands + created_commands

    def _commands_for_individual(self, commands, individual):
        linked_field = self._linked_field_name()
        referenced_ids = set()
        for command in commands:
            if command[0] == Command.SET:
                referenced_ids.update(command[2])
            elif command[0] != Command.CREATE:
                referenced_ids.add(command[1])
        owner_of_line = {
            line.id: line[linked_field].id
            for line in self.browse(list(referenced_ids)).exists()
        }

        def owned(line_id):
            return owner_of_line.get(line_id) == individual.id

        result = []
        for command in commands:
            if command[0] in (Command.CREATE, Command.CLEAR):
                result.append(command)
            elif command[0] == Command.SET:
                result.append(
                    Command.set([line_id for line_id in command[2] if owned(line_id)])
                )
            elif owned(command[1]):
                result.append(command)
        return result
