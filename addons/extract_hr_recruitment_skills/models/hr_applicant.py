from __future__ import annotations

import logging

from odoo import models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    def _update_from_extraction(self, result) -> None:
        self.check_singleton()
        super()._update_from_extraction(result)

        names = self._get_extract_skill_names(result.flat().get("skills"))
        _debug.pipeline("cv_skills_read", applicant=self, names=len(names))
        if names:
            self._add_extracted_skills(names)

    def _get_extract_skill_names(self, skills) -> list[str]:
        # `resume.skills` declares a row and requires its name, and a bare
        # "Python" is read as that one required key, so both shapes a model
        # might answer with arrive here as a row that has a name.
        return [name for skill in skills or () if (name := skill["name"].strip())]

    def _add_extracted_skills(self, names: list[str]) -> None:
        self.check_singleton()
        catalogue = self.env["hr.skill"].search(
            Domain.OR([Domain("name", "=ilike", name) for name in names])
        )
        by_name = {skill.name.casefold(): skill for skill in catalogue}

        wanted = self.env["hr.skill"]
        for name in names:
            skill = by_name.get(name.casefold())
            if skill:
                wanted |= skill
            else:
                _debug.logic(
                    "cv_skill_unknown",
                    reason="not_in_the_catalogue",
                    applicant=self,
                    name=name,
                )
                _logger.info(
                    "CV names the skill %r, which the catalogue does not carry", name
                )

        missing = wanted - self.applicant_skill_ids.skill_id
        vals = []
        for skill in missing:
            levels = skill.skill_type_id.skill_level_ids
            level = levels.filtered("default_level")[:1] or levels[:1]
            if not level:
                _debug.logic(
                    "cv_skill_dropped",
                    reason="skill_type_has_no_level",
                    applicant=self,
                    skill=skill,
                )
                _logger.info(
                    "Skill %r has no level to assign; not attached", skill.name
                )
                continue
            vals.append(
                {
                    "applicant_id": self.id,
                    "skill_id": skill.id,
                    "skill_type_id": skill.skill_type_id.id,
                    "skill_level_id": level.id,
                }
            )
        _debug.pipeline(
            "cv_skills_attached",
            applicant=self,
            named=len(names),
            in_catalogue=wanted,
            already_held=wanted & self.applicant_skill_ids.skill_id,
            attached=len(vals),
        )
        if vals:
            self.env["hr.applicant.skill"].create(vals)
