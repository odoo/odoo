# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    applicant_skill_ids = fields.One2many(
        "hr.applicant.skill", "applicant_id", string="Skills", copy=True
    )
    current_applicant_skill_ids = fields.One2many(
        comodel_name="hr.applicant.skill",
        inverse_name="applicant_id",
        compute="_compute_current_applicant_skill_ids",
        readonly=False,
    )
    skill_ids = fields.Many2many("hr.skill", compute="_compute_skill_ids", store=True)
    matching_skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        string="Matching Factors",
        compute="_compute_matching_skill_ids",
    )
    missing_skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        string="Missing Factors",
        compute="_compute_matching_skill_ids",
    )
    matching_score = fields.Integer(string="Matching Score", compute="_compute_matching_score", store=True)
    degree_score = fields.Integer(string="Degree Score", compute="_compute_matching_score", store=True)
    skills_score = fields.Integer(string="Skills Score", compute="_compute_matching_score", store=True)
    job_matching_score = fields.Integer(
        string="Job Matching Score",
        compute="_compute_job_matching_score",
        compute_sql="_compute_sql_job_matching_score",
        compute_sudo=True,
        aggregator=None,
    )
    is_degree_score_matching = fields.Boolean(string="Degree Score Matching",
        compute="_compute_matching_skill_ids")
    job_expected_degree = fields.Many2one('hr.recruitment.degree', related='job_id.expected_degree',
        string='Job Degree', readonly=True)

    @api.depends("applicant_skill_ids")
    def _compute_current_applicant_skill_ids(self):
        current_applicant_skill_by_applicant = self.applicant_skill_ids._get_current_skills_by_applicant()
        for applicant in self:
            applicant.current_applicant_skill_ids = current_applicant_skill_by_applicant[applicant.id]

    @api.depends("applicant_skill_ids.skill_id")
    def _compute_skill_ids(self):
        for applicant in self:
            applicant.skill_ids = applicant.applicant_skill_ids.skill_id

    @api.depends_context("active_job_id")
    @api.depends("current_applicant_skill_ids", "type_id", "job_id", "job_id.job_skill_ids", "job_id.expected_degree")
    def _compute_matching_skill_ids(self):
        matching_job_from_context = self._get_matching_job_from_context()
        for applicant in self:
            job = matching_job_from_context or applicant.job_id
            if not job or not (job.current_job_skill_ids or job.expected_degree):
                applicant.matching_skill_ids = False
                applicant.missing_skill_ids = False
                applicant.is_degree_score_matching = False
                continue
            job_skills = job.current_job_skill_ids.skill_id
            applicant.matching_skill_ids = applicant.current_applicant_skill_ids.skill_id & job_skills
            applicant.missing_skill_ids = job_skills - applicant.matching_skill_ids
            applicant.is_degree_score_matching = (
                bool(job.expected_degree) and applicant.type_id.score >= job.expected_degree.sudo().score
            )

    @api.depends("current_applicant_skill_ids", "type_id", "job_id", "job_id.job_skill_ids", "job_id.expected_degree")
    def _compute_matching_score(self):
        for applicant in self:
            applicant.update(applicant._get_matching_scores(applicant.job_id))

    @api.depends_context("active_job_id")
    @api.depends("current_applicant_skill_ids", "type_id")
    def _compute_job_matching_score(self):
        job = self._get_matching_job_from_context()
        if not job:
            self.job_matching_score = 0
            return
        for applicant in self:
            applicant.job_matching_score = applicant._get_matching_scores(job)["matching_score"]

    def _compute_sql_job_matching_score(self, table):
        job = self._get_matching_job_from_context()
        if not job:
            # cast to int4 as a bare 0 in ORDER BY is read as a column position
            return SQL("0::int4")
        job_levels = job._get_current_level_by_skill()
        totals = table._make_alias("job_matching_skills")
        # Use a LEFT JOIN so that the applicants having none of the job's skills stay in the search, with a skills
        # total of 0
        table._query.add_join(
            kind="LEFT JOIN",
            alias=totals,
            table=SQL(
                """(SELECT applicant_level.applicant_id,
                           SUM(LEAST(applicant_level.level_progress, job_level.level_progress * 2)) AS skills_total
                      FROM %(applicant_levels)s AS applicant_level
                      JOIN %(job_levels)s AS job_level USING (skill_id)
                  GROUP BY applicant_level.applicant_id)""",
                applicant_levels=self._get_current_level_by_skill_sql(skills=job.current_job_skill_ids.skill_id),
                job_levels=self._get_levels_sql(job_levels),
            ),
            condition=SQL("%s = %s", totals.applicant_id, table.id),
        )
        job_degree = job.expected_degree.score * 100
        return self._get_matching_score_sql(
            job_degree=job_degree,
            job_total=sum(job_levels.values()) + job_degree,
            applicant_degree=SQL("COALESCE(%s, 0) * 100", table.type_id.score),
            skills_total=SQL("COALESCE(%s, 0)", totals.skills_total),
        )

    def _get_matching_job_from_context(self):
        """
        Return the active job from the context. Used to calculate matching score for the applicants.

        :return: the ``hr.job`` of ``active_job_id`` in the context, empty if not given
        """
        return self.env["hr.job"].browse(self.env.context.get("active_job_id"))

    def _get_current_level_by_skill(self):
        """
        Return the highest current level of the applicant per skill. Only certifications can have multiple active levels
        for the same skill. More info in the docstring of ``_check_not_overlapping_regular_skill``.

        :return: ``{skill: level_progress}``, with ``hr.skill`` records as keys
        """
        self.ensure_one()
        return {
            skill: max(applicant_skills.mapped("level_progress"))
            for skill, applicant_skills in self.current_applicant_skill_ids.grouped("skill_id").items()
        }

    @api.model
    def _get_current_level_by_skill_sql(self, skills):
        """
        SQL version of ``_get_current_level_by_skill``, for all applicants at once.

        :param skills: ``hr.skill`` to limit the levels to
        :return: a query with the columns ``applicant_id``, ``skill_id`` and ``level_progress``
        """
        today = fields.Date.context_today(self)
        query = self.env["hr.applicant.skill"]._search(
            Domain("skill_id", "in", skills.ids)
            & (
                Domain("valid_to", "=", False) | Domain("valid_to", ">=", today) | Domain("is_certification", "=", True)
            ),
        )
        query.groupby = SQL("%s, %s", query.table.applicant_id, query.table.skill_id)
        return query.subselect(
            SQL(
                """%(applicant_id)s AS applicant_id,
                   %(skill_id)s AS skill_id,
                   COALESCE(
                       MAX(%(level)s) FILTER (WHERE %(valid_to)s IS NULL OR %(valid_to)s >= %(today)s),
                       (ARRAY_AGG(%(level)s ORDER BY %(valid_to)s DESC, %(level)s DESC))[1]
                   ) AS level_progress""",
                applicant_id=query.table.applicant_id,
                skill_id=query.table.skill_id,
                level=query.table.level_progress,
                valid_to=query.table.valid_to,
                today=today,
            ),
        )

    @api.model
    def _get_levels_sql(self, levels):
        """
        Turn the levels of a single job or applicant into an SQL table, so they can be joined with the levels of
        all the searched applicants or jobs given by ``_get_current_level_by_skill_sql``.

        :param levels: ``{skill: level_progress}`` from ``_get_current_level_by_skill``
        :return: a query with the columns ``skill_id`` and ``level_progress``
        """
        return SQL(
            "(SELECT * FROM unnest(%(skill_ids)s::int4[], %(levels)s::int4[]) AS level(skill_id, level_progress))",
            skill_ids=[skill.id for skill in levels],
            levels=list(levels.values()),
        )

    def _get_matching_scores(self, job):
        """
        Calculate how well the applicant matches the requirements of the given job on the scale 0-100, based on the
        education degree, skills and both. Each applicant skill counts up to twice the skill level of the job so a
        score can theoretically exceed 100. Note: Keep this method in sync with ``_get_matching_score_sql``.

        :param job: ``hr.job`` to match against, empty when the applicant has none (e.g. a talent), which scores 0
        :return: the ``degree_score``, ``skills_score`` and their sum ``matching_score``
        """
        self.ensure_one()
        scores = dict.fromkeys(("degree_score", "skills_score", "matching_score"), 0)
        if not job:
            return scores
        job_levels = job._get_current_level_by_skill()
        job_degree = job.expected_degree.score * 100
        job_total = sum(job_levels.values()) + job_degree
        if not job_total:
            return scores
        applicant_levels = self._get_current_level_by_skill()
        applicant_degree = self.type_id.score * 100 if job_degree > 1 else 0
        skills_total = sum(
            min(applicant_levels[skill], level * 2) for skill, level in job_levels.items() if skill in applicant_levels
        )
        scores["degree_score"] = round(100 * applicant_degree / job_total)
        scores["skills_score"] = round(100 * skills_total / job_total)
        scores["matching_score"] = scores["degree_score"] + scores["skills_score"]
        return scores

    @api.model
    def _get_matching_score_sql(self, job_degree, job_total, applicant_degree, skills_total):
        """
        SQL version of the ``matching_score`` portion of ``_get_matching_scores``, from the same totals. Each total
        is a number when it belongs to the job or applicant in the context (the same for every row), or SQL when it
        belongs to the searched records (different on each row). E.g. when searching applicants for a job, the job
        totals are numbers and the applicant totals are SQL.

        :param job_degree: degree expected by the job, out of 100
        :param job_total: ``job_degree`` plus the levels of the job skills
        :param applicant_degree: degree of the applicant, out of 100
        :param skills_total: levels of the applicant in the job skills, each up to twice the level of the job
        :return: the score as SQL, 0 when the job has no skills or degree
        """
        applicant_degree = SQL(
            "CASE WHEN %(job_degree)s > 1 THEN %(applicant_degree)s ELSE 0 END",
            job_degree=job_degree,
            applicant_degree=applicant_degree,
        )

        def percent(total):
            # float8 so that ROUND() rounds half to even like round(), NULLIF() to not divide by 0
            return SQL("ROUND(100::float8 * %(total)s / NULLIF(%(job_total)s, 0))", total=total, job_total=job_total)

        return SQL(
            "COALESCE((%(degree_score)s + %(skills_score)s)::int4, 0)",
            degree_score=percent(applicant_degree),
            skills_score=percent(skills_total),
        )

    def _get_employee_create_vals(self):
        vals = super()._get_employee_create_vals()
        vals["employee_skill_ids"] = [
            (
                0,
                0,
                {
                    "skill_id": applicant_skill.skill_id.id,
                    "skill_level_id": applicant_skill.skill_level_id.id,
                    "skill_type_id": applicant_skill.skill_type_id.id,
                },
            )
            for applicant_skill in self.applicant_skill_ids
        ]
        return vals

    def _map_applicant_skill_ids_to_other_applicant_skill_ids(self, other_applicant, vals):
        """
        The applicant_skills_ids contains a list of ORM tuples i.e (command, record ID, {values})
        The challenge lies in the uniqueness of the record ID in this tuple. Each skill (e.g., 'arabic')
        has a distinct ID per applicant, i.e arabic in applicant 1 will have a different id from arabic in
        applicant 2. This means the content of applicant_skills_ids is unique for each record and attempting
        to pass it directly (e.g., applicant.pool_applicant_id.write(vals)) won't yield results so we must
        update each tuple to have the correct command and record ID for the other applicant

        :param other_applicant: the other @hr.applicant the skill_ids will be mapped to
        :param vals: list of CREATE, WRITE or UNLINK commands with skill_ids relevant to the applicant
        :return: list of CREATE, WRITE or UNLINK commands with skill_ids relevant to the other applicant
        """
        applicant_skills = {a.id: a.skill_id.id for a in self.applicant_skill_ids}
        applicant_skills_type = {a.id: a.skill_type_id.id for a in self.applicant_skill_ids}
        other_applicant_skills = {a.skill_id.id: a.id for a in other_applicant.applicant_skill_ids}
        mapped_commands = []
        for command in vals.get("applicant_skill_ids"):
            command_number = command[0]
            record_id = command[1]
            if command_number == Command.UPDATE:
                values = command[2]
                if applicant_skills[record_id] in other_applicant_skills:
                    mapped_command = Command.update(other_applicant_skills[applicant_skills[record_id]], values)
                    mapped_commands.append(mapped_command)
                else:
                    mapped_command = Command.create(
                        {
                            "skill_id": applicant_skills[record_id],
                            "skill_type_id": applicant_skills_type[record_id],
                            "skill_level_id": values["skill_level_id"],
                        },
                    )
                    mapped_commands.append(mapped_command)
            elif command_number == Command.DELETE:
                if applicant_skills[record_id] in other_applicant_skills:
                    mapped_command = Command.delete(other_applicant_skills[applicant_skills[record_id]])
                    mapped_commands.append(mapped_command)
            else:
                mapped_commands.append(command)
        return mapped_commands

    def action_job_add_applicants(self):
        res = super().action_job_add_applicants()
        if len(self.ids) == 1:
            res["context"]["active_applicant_id"] = self.id
            applicant_job_ids = self.job_id
            if self.pool_applicant_id:
                applicant_job_ids += self.pool_applicant_id.linked_applicant_ids.job_id
            else:
                domain = self._get_similar_applicants_domain()
                applicant_job_ids += self.env["hr.applicant"].search(domain).job_id
            res["context"]["active_applicant_job_ids"] = applicant_job_ids.ids
        return res

    @api.model_create_multi
    def create(self, vals_list):
        if not self:
            # This is required for the talent pool mechanism to work. Duplicating an hr.applicant record without this
            # check will cause the skills to not be duplicated or disappear randomly.
            for vals in vals_list:
                vals["applicant_skill_ids"] = vals.pop("current_applicant_skill_ids", []) + vals.get("applicant_skill_ids", [])
        return super().create(vals_list)

    def write(self, vals):
        if "current_applicant_skill_ids" in vals or "applicant_skill_ids" in vals:
            skills = vals.pop("current_applicant_skill_ids", []) + vals.get("applicant_skill_ids", [])
            original_vals = vals.copy()
            original_vals["applicant_skill_ids"] = skills
            vals["applicant_skill_ids"] = self.env["hr.applicant.skill"]._get_transformed_commands(skills, self)
            if not self.env.context.get('skills_synced'):
                for pool_applicant, current_applicants in self.grouped('pool_applicant_id').items():
                    # Modify the skill values for the remaining applicants in the talent pool
                    source_applicant = current_applicants[0]
                    other_applicants = pool_applicant.linked_applicant_ids - current_applicants
                    for applicant in other_applicants:
                        mapped_skills = source_applicant._map_applicant_skill_ids_to_other_applicant_skill_ids(applicant, original_vals)
                        applicant.with_context(skills_synced=True).write({"applicant_skill_ids": mapped_skills})
        return super().write(vals)

    @api.depends_context("show_matching_score_in_name", "active_job_id", "formatted_display_name")
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get("show_matching_score_in_name", False):
            # in formatted names (many2one dropdowns), "\t" adds a gap and "--text--" is muted
            name_format = "%s \t --%s%%--" if self.env.context.get("formatted_display_name") else "%s (%s%%)"
            for applicant in self:
                if score := applicant.job_matching_score:
                    applicant.display_name = name_format % (applicant.display_name or applicant.name, score)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        if not (self.env.context.get("show_matching_score_in_name") and self._get_matching_job_from_context()):
            return super().name_search(name=name, domain=domain, operator=operator, limit=limit)
        domain = Domain("display_name", operator, name) & Domain(domain or Domain.TRUE)
        records = self.search_fetch(
            domain,
            ["display_name"],
            order="job_matching_score desc, id",
            limit=limit,
        )
        return [(record.id, record.display_name) for record in records.sudo()]
