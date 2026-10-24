from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class HrJob(models.Model):
    _inherit = "hr.job"

    applicant_matching_score = fields.Integer(
        string="Matching Score(%)",
        compute="_compute_applicant_matching_score",
        compute_sql="_compute_sql_applicant_matching_score",
        compute_sudo=True,
        aggregator=None,
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    matching_applicant_skill_ids = fields.Many2many(
        string="Matching Skills",
        comodel_name="hr.skill",
        compute="_compute_matching_applicant_skill_ids",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    missing_applicant_skill_ids = fields.Many2many(
        string="Missing Skills",
        comodel_name="hr.skill",
        compute="_compute_matching_applicant_skill_ids",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )

    @api.depends_context("active_applicant_id")
    @api.depends("job_skill_ids", "expected_degree")
    def _compute_applicant_matching_score(self):
        applicant = self._get_matching_applicant_from_context()
        if not applicant:
            self.applicant_matching_score = 0
            return
        for job in self:
            job.applicant_matching_score = applicant._get_matching_scores(job)["matching_score"]

    def _compute_sql_applicant_matching_score(self, table):
        applicant = self._get_matching_applicant_from_context()
        if not applicant:
            # cast to int4 as a bare 0 in ORDER BY is read as a column position
            return SQL("0::int4")
        applicant_levels = applicant._get_current_level_by_skill()
        totals = table._make_alias("applicant_matching_skills")
        # Use a LEFT JOIN so that the jobs without skills stay in the search, with totals of 0, and another one so
        # that job_total also counts the job skills the applicant lacks
        table._query.add_join(
            kind="LEFT JOIN",
            alias=totals,
            table=SQL(
                """(SELECT job_level.job_id,
                           SUM(job_level.level_progress) AS job_total,
                           SUM(LEAST(COALESCE(applicant_level.level_progress, 0), job_level.level_progress * 2))
                               AS skills_total
                      FROM %(job_levels)s AS job_level
                 LEFT JOIN %(applicant_levels)s AS applicant_level USING (skill_id)
                  GROUP BY job_level.job_id)""",
                job_levels=self._get_current_level_by_skill_sql(),
                applicant_levels=applicant._get_levels_sql(applicant_levels),
            ),
            condition=SQL("%s = %s", totals.job_id, table.id),
        )
        job_degree = SQL("COALESCE(%s, 0) * 100", table.expected_degree.score)
        return applicant._get_matching_score_sql(
            job_degree=job_degree,
            job_total=SQL(
                "%(job_degree)s + COALESCE(%(job_skills_total)s, 0)",
                job_degree=job_degree,
                job_skills_total=totals.job_total,
            ),
            applicant_degree=applicant.type_id.score * 100,
            skills_total=SQL("COALESCE(%s, 0)", totals.skills_total),
        )

    @api.depends_context("active_applicant_id")
    @api.depends("job_skill_ids")
    def _compute_matching_applicant_skill_ids(self):
        applicant = self._get_matching_applicant_from_context()
        applicant_skills = applicant.current_applicant_skill_ids.skill_id
        for job in self:
            job_skills = job.current_job_skill_ids.skill_id
            if not applicant or not job_skills:
                job.matching_applicant_skill_ids = False
                job.missing_applicant_skill_ids = False
                continue
            job.matching_applicant_skill_ids = job_skills & applicant_skills
            job.missing_applicant_skill_ids = job_skills - applicant_skills

    def _get_matching_applicant_from_context(self):
        """
        Return the active applicant from the context. Used to calculate matching score for the jobs.

        :return: the ``hr.applicant`` of ``active_applicant_id`` in the context, empty if not given
        """
        return self.env["hr.applicant"].browse(self.env.context.get("active_applicant_id"))

    def _get_current_level_by_skill(self):
        """
        Return the highest current required level of the job per skill. Only certifications can have multiple active
        levels for the same skill. More info in the docstring of ``_check_not_overlapping_regular_skill``.

        :return: ``{skill: level_progress}``, with ``hr.skill`` records as keys
        """
        self.ensure_one()
        return {
            skill: max(job_skills.mapped("level_progress"))
            for skill, job_skills in self.current_job_skill_ids.grouped("skill_id").items()
        }

    @api.model
    def _get_current_level_by_skill_sql(self):
        """
        SQL version of ``_get_current_level_by_skill``, for all jobs at once.

        :return: a query with the columns ``job_id``, ``skill_id`` and ``level_progress``
        """
        today = fields.Date.context_today(self)
        query = self.env["hr.job.skill"]._search(
            Domain("skill_type_id.active", "=", True)
            & (Domain("valid_to", "=", False) | Domain("valid_to", ">=", today)),
        )
        query.groupby = SQL("%s, %s", query.table.job_id, query.table.skill_id)
        return query.subselect(
            SQL(
                "%(job_id)s AS job_id, %(skill_id)s AS skill_id, MAX(%(level)s) AS level_progress",
                job_id=query.table.job_id,
                skill_id=query.table.skill_id,
                level=query.table.level_progress,
            ),
        )

    @api.depends_context("show_matching_score_in_name", "active_applicant_id", "formatted_display_name")
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get("show_matching_score_in_name", False):
            # in formatted names (many2one dropdowns), "\t" adds a gap and "--text--" is muted
            name_format = "%s \t --%s%%--" if self.env.context.get("formatted_display_name") else "%s (%s%%)"
            for job in self:
                if score := job.applicant_matching_score:
                    job.display_name = name_format % (job.display_name or job.name, score)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        if not (self.env.context.get("show_matching_score_in_name") and self._get_matching_applicant_from_context()):
            return super().name_search(name=name, domain=domain, operator=operator, limit=limit)
        domain = Domain("display_name", operator, name) & Domain(domain or Domain.TRUE)
        records = self.search_fetch(
            domain,
            ["display_name"],
            order="applicant_matching_score desc, id",
            limit=limit,
        )
        return [(record.id, record.display_name) for record in records.sudo()]

    def action_job_add_applicants(self):
        res = super().action_job_add_applicants()
        if len(self.ids) == 1:
            res["context"]["active_job_id"] = self.id
            res["context"]["active_job_applicant_ids"] = self.application_ids.ids
        return res
