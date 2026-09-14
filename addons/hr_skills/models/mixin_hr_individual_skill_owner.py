from odoo import api, fields, models
from odoo.fields import Domain


class MixinHrIndividualSkillOwner(models.AbstractModel):
    _name = "mixin.hr.individual.skill.owner"
    _description = "Owner of individual skills"

    def _individual_skill_field_name(self):
        raise NotImplementedError

    def _current_individual_skill_field_name(self):
        raise NotImplementedError

    def _individual_skill_command_field_names(self):
        return (
            self._current_individual_skill_field_name(),
            self._individual_skill_field_name(),
        )

    def _individual_skill_model(self):
        return self.env[self._fields[self._individual_skill_field_name()].comodel_name]

    @api.depends(
        lambda self: [
            f"{self._individual_skill_field_name()}.{field_name}"
            for field_name in ("valid_to", "skill_id", "is_certification")
        ]
    )
    def _compute_current_individual_skill_ids(self):
        skill_model = self._individual_skill_model()
        current_by_owner = (
            self[self._individual_skill_field_name()]
            ._current_individual_skills()
            .grouped(skill_model._linked_field_name())
        )
        current_field = self._current_individual_skill_field_name()
        for owner in self:
            owner[current_field] = current_by_owner.get(owner, skill_model)

    @api.depends(
        lambda self: [
            f"{self._individual_skill_field_name()}.{field_name}"
            for field_name in ("valid_from", "valid_to", "skill_id")
        ]
    )
    def _compute_skill_ids(self):
        stored_field = self._individual_skill_field_name()
        for owner in self:
            owner.skill_ids = owner[stored_field]._held_individual_skills().skill_id

    def _domain_owning_individual_skills(self, skill_domain):
        return Domain(
            self._individual_skill_field_name(),
            "in",
            self._individual_skill_model()._search(skill_domain),
        )

    def _search_current_individual_skill_ids(self, operator, value):
        if operator not in ("in", "not in", "any"):
            raise NotImplementedError
        if operator == "any" and isinstance(value, Domain):
            skill_domain = value
        else:
            skill_domain = Domain("id", "in", value)
        skill_model = self._individual_skill_model()
        result = self._domain_owning_individual_skills(
            skill_model._domain_current(fields.Date.today()) & skill_domain
        )
        return ~result if operator == "not in" else result

    def _search_skill_ids(self, operator, value):
        if operator not in ("in", "not in"):
            raise NotImplementedError
        skill_model = self._individual_skill_model()
        result = self._domain_owning_individual_skills(
            skill_model._domain_held(fields.Date.today())
            & Domain("skill_id", "in", value)
        )
        return ~result if operator == "not in" else result

    def _pop_individual_skill_commands(self, vals):
        commands = []
        for field_name in self._individual_skill_command_field_names():
            commands += vals.pop(field_name, None) or []
        return commands

    @api.model_create_multi
    def create(self, vals_list):
        stored_field = self._individual_skill_field_name()
        for vals in vals_list:
            if not (set(self._individual_skill_command_field_names()) & vals.keys()):
                continue
            if commands := self._pop_individual_skill_commands(vals):
                vals[stored_field] = (
                    self._individual_skill_model()._get_transformed_commands(
                        commands, self.browse()
                    )
                )
        return super().create(vals_list)

    def write(self, vals):
        if not (set(self._individual_skill_command_field_names()) & vals.keys()):
            return super().write(vals)
        commands = self._pop_individual_skill_commands(vals)
        stored_field = self._individual_skill_field_name()
        skill_model = self._individual_skill_model()
        if len(self) == 1:
            vals[stored_field] = skill_model._get_transformed_commands(commands, self)
            return super().write(vals)
        result = super().write(vals) if vals else True
        self.check_access("write")
        skill_model._apply_individual_skill_commands(
            skill_model._transform_commands_by_individual(
                skill_model._commands_by_individual(commands, self)
            )
        )
        return result
