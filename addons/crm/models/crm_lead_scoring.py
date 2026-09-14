import logging
from collections import OrderedDict, defaultdict
from datetime import datetime
from itertools import batched

from odoo import fields, models, modules, tools
from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

PLS_COMPUTE_BATCH_STEP = 50000
PLS_UPDATE_BATCH_STEP = 5000


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _pls_tally_frequencies(self, frequencies, leads_fields, frequency_team_ids):
        result = {
            team_id: {
                field: {"won_total": 0, "lost_total": 0} for field in leads_fields
            }
            for team_id in [*frequency_team_ids, -1]
        }
        for frequency in frequencies:
            field, value = frequency["variable"], frequency["value"]

            if (
                field == "tag_id"
                and (frequency["won_count"] + frequency["lost_count"]) < 50
            ):
                continue

            if frequency.team_id:
                team_result = result[frequency.team_id.id]
                team_result[field][value] = {
                    "won": frequency["won_count"],
                    "lost": frequency["lost_count"],
                }
                team_result[field]["won_total"] += frequency["won_count"]
                team_result[field]["lost_total"] += frequency["lost_count"]

            all_teams = result[-1][field]
            all_teams.setdefault(value, {"won": 0, "lost": 0})
            all_teams[value]["won"] += frequency["won_count"]
            all_teams[value]["lost"] += frequency["lost_count"]
            all_teams["won_total"] += frequency["won_count"]
            all_teams["lost_total"] += frequency["lost_count"]
        return result

    def _pls_team_priors(self, result):
        first_stage_id = self._pls_first_stage()
        priors = {}
        for team_id, team_result in result.items():
            won, lost, total = self._pls_get_won_lost_total_count(
                team_result, first_stage_id=first_stage_id
            )
            (
                team_result["team_won"],
                team_result["team_lost"],
                team_result["team_total"],
            ) = won, lost, total
            if won and lost:
                priors[team_id] = (won, lost, won / total, lost / total)
        return priors

    def _pls_get_naive_bayes_probabilities(self, batch_mode=False, is_tooltip=False):
        lead_probabilities = {}
        if not self:
            return lead_probabilities, {}

        tooltip_data = {}
        if is_tooltip:
            self.check_singleton()
            tooltip_data = {
                "probability": 0.0,
                "scores": [],
            }

        domain = []
        if batch_mode:
            domain = [
                ("active", "=", True),
                ("id", "in", self.ids),
                ("won_status", "=", "pending"),
            ]
        leads_values_dict = self._pls_get_lead_pls_values(domain=domain)

        if not leads_values_dict:
            return lead_probabilities, tooltip_data

        leads_fields = set()
        won_leads = set()
        won_stage_ids = self.env["crm.stage"].search([("is_won", "=", True)]).ids
        for lead_id, values in leads_values_dict.items():
            for field, value in values["values"]:
                if field == "stage_id" and value in won_stage_ids:
                    won_leads.add(lead_id)
                leads_fields.add(field)
        leads_fields = sorted(leads_fields)
        frequencies = self.env["crm.lead.scoring.frequency"].search(
            [("variable", "in", list(leads_fields))], order="team_id asc, id"
        )

        frequency_teams = frequencies.mapped("team_id")
        frequency_team_ids = [team.id for team in frequency_teams]

        if is_tooltip and self.team_id & frequency_teams:
            frequency_team_ids = [self.team_id.id]
            frequencies = frequencies.filtered(
                lambda frequency: frequency.team_id & self.team_id
            )

        result = self._pls_tally_frequencies(
            frequencies, leads_fields, frequency_team_ids
        )
        team_priors = self._pls_team_priors(result)

        for lead_id, lead_values in leads_values_dict.items():
            lead_fields = [value[0] for value in lead_values.get("values", [])]
            if "stage_id" not in lead_fields:
                lead_probabilities[lead_id] = 0
                continue
            if lead_id in won_leads:
                lead_probabilities[lead_id] = 100
                continue

            lead_team_id = (
                lead_values["team_id"] if lead_values["team_id"] in result else -1
            )
            prior = team_priors.get(lead_team_id)
            if prior is None:
                continue
            team_won, team_lost, p_won, p_lost = prior

            s_lead_won, s_lead_lost = p_won, p_lost
            for field, value in lead_values["values"]:
                field_result = result[lead_team_id].get(field)
                value = value.origin if hasattr(value, "origin") else value
                value_result = field_result.get(str(value)) if field_result else False
                if value_result:
                    total_won = (
                        team_won if field == "stage_id" else field_result["won_total"]
                    )
                    total_lost = (
                        team_lost if field == "stage_id" else field_result["lost_total"]
                    )
                    if not total_won or not total_lost:
                        continue
                    p_field_value_won = value_result["won"] / total_won
                    p_field_value_lost = value_result["lost"] / total_lost
                    s_lead_won *= p_field_value_won
                    s_lead_lost *= p_field_value_lost

                    if is_tooltip:
                        score = (
                            1 - p_field_value_lost
                            if field == "stage_id"
                            else p_field_value_won
                            / (p_field_value_won + p_field_value_lost)
                        )
                        tooltip_data["scores"].append((score, field, value))
            probability = s_lead_won / (s_lead_won + s_lead_lost)
            lead_probabilities[lead_id] = min(
                max(round(100 * probability, 2), 0.01), 99.99
            )

        if tooltip_data and self.id in lead_probabilities:
            tooltip_data["probability"] = lead_probabilities[self.id]

        return lead_probabilities, tooltip_data

    def _pls_increment_frequencies(self, from_state=None, to_state=None):
        new_frequencies_by_team, existing_frequencies_by_team = (
            self._pls_prepare_update_frequency_table(
                target_state=from_state or to_state
            )
        )

        self._pls_update_frequency_table(
            new_frequencies_by_team,
            1 if to_state else -1,
            existing_frequencies_by_team=existing_frequencies_by_team,
        )

    def _cron_update_automated_probabilities(self):
        cron_start_date = datetime.now()
        self._rebuild_pls_frequency_table()
        self._update_automated_probabilities()
        _logger.info(
            "Predictive Lead Scoring : Cron duration = %d seconds"
            % ((datetime.now() - cron_start_date).total_seconds())
        )

    def _rebuild_pls_frequency_table(self):
        try:
            self.browse().check_access("unlink")
        except AccessError:
            raise UserError(_("You don't have the access needed to run this cron."))
        else:
            self.env.cr.execute("TRUNCATE TABLE crm_lead_scoring_frequency")

        new_frequencies_by_team, unused = self._pls_prepare_update_frequency_table(
            rebuild=True
        )
        self._pls_update_frequency_table(new_frequencies_by_team, 1)

        _logger.info(
            "Predictive Lead Scoring : crm.lead.scoring.frequency table rebuilt"
        )

    def _update_automated_probabilities(self):
        pls_start_date = self._pls_get_safe_start_date()
        if not pls_start_date:
            return

        pending_lead_domain = [
            ("stage_id", "!=", False),
            ("create_date", ">=", pls_start_date),
            ("won_status", "=", "pending"),
        ]
        leads_to_update = self.env["crm.lead"].search(pending_lead_domain)
        leads_to_update_count = len(leads_to_update)

        lead_probabilities = {}
        for i in range(0, leads_to_update_count, PLS_COMPUTE_BATCH_STEP):
            leads_to_update_part = leads_to_update[i : i + PLS_COMPUTE_BATCH_STEP]
            batch_probabilites, _unused = (
                leads_to_update_part._pls_get_naive_bayes_probabilities(batch_mode=True)
            )
            lead_probabilities.update(batch_probabilites)
        _logger.info("Predictive Lead Scoring : New automated probabilities computed")

        probability_leads = defaultdict(list)
        for lead_id, probability in sorted(lead_probabilities.items()):
            probability_leads[probability].append(lead_id)

        update_sql = """UPDATE crm_lead
                        SET automated_probability = %s,
                            probability = CASE WHEN (probability = automated_probability OR probability is null)
                                               THEN (%s)
                                               ELSE (probability)
                                          END
                        WHERE id = ANY(%s)"""

        transactions_count, transactions_failed_count = 0, 0
        cron_update_lead_start_date = datetime.now()
        auto_commit = not modules.module.current_test
        self.flush_model()
        for probability, probability_lead_ids in probability_leads.items():
            for lead_ids_current in batched(
                probability_lead_ids, PLS_UPDATE_BATCH_STEP
            ):
                transactions_count += 1
                try:
                    self.env.cr.execute(
                        update_sql, (probability, probability, list(lead_ids_current))
                    )
                    if auto_commit:
                        self.env.cr.commit()
                except Exception as e:
                    _logger.warning(
                        "Predictive Lead Scoring : update transaction failed. Error: %s"
                        % e
                    )
                    transactions_failed_count += 1
        self.invalidate_model()

        _logger.info(
            "Predictive Lead Scoring : All automated probabilities updated (%d leads / %d transactions (%d failed) / %d seconds)"
            % (
                leads_to_update_count,
                transactions_count,
                transactions_failed_count,
                (datetime.now() - cron_update_lead_start_date).total_seconds(),
            )
        )

    def _pls_prepare_update_frequency_table(self, rebuild=False, target_state=False):
        pls_start_date = self._pls_get_safe_start_date()
        if not pls_start_date:
            return {}, {}

        if rebuild:
            pls_leads = self
        else:
            pls_leads = self.filtered(
                lambda lead: (
                    fields.Date.to_date(pls_start_date)
                    <= fields.Date.to_date(lead.create_date)
                )
            )
            if not pls_leads:
                return {}, {}

        if rebuild:
            domain = [
                ("create_date", ">=", pls_start_date),
                ("won_status", "in", ["lost", "won"]),
            ]
            team_ids = self.env["team.team"].with_context(active_test=False).search(
                [("use_sale", "=", True)]
            ).ids + [0]
        else:
            domain = [("id", "in", pls_leads.ids)]
            team_ids = pls_leads.mapped("team_id").ids + [0]

        leads_values_dict = pls_leads._pls_get_lead_pls_values(domain=domain)

        leads_frequency_values_by_team = dict((team_id, []) for team_id in team_ids)
        leads_pls_fields = set()
        for values in leads_values_dict.values():
            team_id = values.get("team_id", 0)
            lead_frequency_values = {"count": 1}
            for field, value in values["values"]:
                if field != "probability":
                    leads_pls_fields.add(field)
                else:
                    lead_probability = value
                if field == "tag_id":
                    leads_frequency_values_by_team[team_id].append(
                        {field: value, "count": 1, "probability": lead_probability}
                    )
                else:
                    lead_frequency_values[field] = value
            leads_frequency_values_by_team[team_id].append(lead_frequency_values)
        leads_pls_fields = sorted(leads_pls_fields)

        new_frequencies_by_team = {}
        for team_id in team_ids:
            new_frequencies_by_team[team_id] = self._pls_prepare_frequencies(
                leads_frequency_values_by_team[team_id],
                leads_pls_fields,
                target_state=target_state,
            )

        existing_frequencies_by_team = {}
        if not rebuild:
            existing_frequencies = self.env["crm.lead.scoring.frequency"].search_read(
                [
                    "&",
                    ("variable", "in", leads_pls_fields),
                    "|",
                    ("team_id", "in", pls_leads.mapped("team_id").ids),
                    ("team_id", "=", False),
                ]
            )
            for frequency in existing_frequencies:
                team_id = frequency["team_id"][0] if frequency.get("team_id") else 0
                if team_id not in existing_frequencies_by_team:
                    existing_frequencies_by_team[team_id] = dict(
                        (field, {}) for field in leads_pls_fields
                    )

                existing_frequencies_by_team[team_id][frequency["variable"]][
                    frequency["value"]
                ] = {
                    "frequency_id": frequency["id"],
                    "won": frequency["won_count"],
                    "lost": frequency["lost_count"],
                }

        return new_frequencies_by_team, existing_frequencies_by_team

    def _pls_update_frequency_table(
        self, new_frequencies_by_team, step, existing_frequencies_by_team=None
    ):
        values_to_update = {}
        values_to_create = []
        if not existing_frequencies_by_team:
            existing_frequencies_by_team = {}
        for team_id, new_frequencies in new_frequencies_by_team.items():
            for field, value in new_frequencies.items():
                current_frequencies = existing_frequencies_by_team.get(team_id, {})
                for param, result in value.items():
                    current_frequency_for_couple = current_frequencies.get(
                        field, {}
                    ).get(param, {})
                    if current_frequency_for_couple:
                        new_won = current_frequency_for_couple["won"] + (
                            result["won"] * step
                        )
                        new_lost = current_frequency_for_couple["lost"] + (
                            result["lost"] * step
                        )
                        values_to_update[
                            current_frequency_for_couple["frequency_id"]
                        ] = {
                            "won_count": new_won if new_won > 0 else 0.1,
                            "lost_count": new_lost if new_lost > 0 else 0.1,
                        }
                        continue

                    values_to_create.append(
                        {
                            "variable": field,
                            "value": param,
                            "won_count": result["won"] + 0.1,
                            "lost_count": result["lost"] + 0.1,
                            "team_id": team_id or None,
                        }
                    )

        LeadScoringFrequency = self.env["crm.lead.scoring.frequency"].sudo()
        for frequency_id, values in values_to_update.items():
            LeadScoringFrequency.browse(frequency_id).write(values)

        if values_to_create:
            LeadScoringFrequency.create(values_to_create)

    def _pls_get_safe_start_date(self):
        str_date = (
            self.env["ir.config_parameter"].sudo().get_param("crm.pls_start_date")
        )
        if not fields.Date.to_date(str_date):
            return False
        return str_date

    def _pls_get_safe_fields(self):
        pls_fields_config = (
            self.env["ir.config_parameter"].sudo().get_param("crm.pls_fields")
        )
        pls_fields = pls_fields_config.split(",") if pls_fields_config else []
        pls_safe_fields = [
            field for field in pls_fields if field in self._fields.keys()
        ]
        return pls_safe_fields

    def _pls_first_stage(self):
        return self.env["crm.stage"].search(
            [("team_ids", "=", False)], order="sequence, id", limit=1
        )

    def _pls_get_won_lost_total_count(self, team_results, first_stage_id=None):
        if first_stage_id is None:
            first_stage_id = self._pls_first_stage()
        if str(first_stage_id.id) not in team_results.get("stage_id", []):
            return 0, 0, 0
        stage_result = team_results["stage_id"][str(first_stage_id.id)]
        return (
            stage_result["won"],
            stage_result["lost"],
            stage_result["won"] + stage_result["lost"],
        )

    def _pls_prepare_frequencies(
        self, lead_values, leads_pls_fields, target_state=None
    ):
        pls_fields = leads_pls_fields.copy()
        frequencies = dict((field, {}) for field in pls_fields)

        stage_ids = self.env["crm.stage"].search_read(
            [], ["sequence", "name", "id"], order="sequence, id"
        )
        stage_sequences = {stage["id"]: stage["sequence"] for stage in stage_ids}

        for values in lead_values:
            if target_state:
                won_count = values["count"] if target_state == "won" else 0
                lost_count = values["count"] if target_state == "lost" else 0
            else:
                won_count = (
                    values["count"] if values.get("probability", 0) == 100 else 0
                )
                lost_count = values["count"] if values.get("probability", 1) == 0 else 0

            if "tag_id" in values:
                frequencies = self._pls_increment_frequency_dict(
                    frequencies, "tag_id", values["tag_id"], won_count, lost_count
                )
                continue

            if "tag_id" in pls_fields:
                pls_fields.remove("tag_id")
            for field in pls_fields:
                if field not in values:
                    continue
                value = values[field]
                if value or field in ("email_state", "phone_state"):
                    if field == "stage_id":
                        if won_count:
                            stages_to_increment = [stage["id"] for stage in stage_ids]
                        else:
                            current_stage_sequence = stage_sequences[value]
                            stages_to_increment = [
                                stage["id"]
                                for stage in stage_ids
                                if stage["sequence"] <= current_stage_sequence
                            ]
                        for stage_id in stages_to_increment:
                            frequencies = self._pls_increment_frequency_dict(
                                frequencies, field, stage_id, won_count, lost_count
                            )
                    else:
                        frequencies = self._pls_increment_frequency_dict(
                            frequencies, field, value, won_count, lost_count
                        )

        return frequencies

    def _pls_increment_frequency_dict(self, frequencies, field, value, won, lost):
        value = str(value)
        if value not in frequencies[field]:
            frequencies[field][value] = {"won": won, "lost": lost}
        else:
            frequencies[field][value]["won"] += won
            frequencies[field][value]["lost"] += lost
        return frequencies

    def _pls_get_lead_pls_values(self, domain=None):
        leads_values_dict = OrderedDict()
        pls_fields = ["stage_id", "team_id"] + self._pls_get_safe_fields()

        use_tags = "tag_ids" in pls_fields
        if use_tags:
            pls_fields.remove("tag_ids")

        if domain:
            self.flush_model()
            query = (
                self.env["crm.lead"]
                .with_context(active_test=False)
                ._search(domain, bypass_access=True)
            )
            table = query.table
            query.order = SQL(
                "%(table)s.team_id asc, %(table)s.id desc", table=SQL.identifier(table)
            )
            sql_fields = [SQL.identifier(field) for field in pls_fields]
            self.env.cr.execute(
                query.select(
                    SQL("id"),
                    SQL("probability"),
                    *sql_fields,
                )
            )
            lead_results = self.env.cr.dictfetchall()

            if use_tags:
                tag_rel_alias = query.left_join(
                    table, "id", "crm_tag_rel", "lead_id", "crm_tag_rel"
                )
                tag_alias = query.left_join(
                    tag_rel_alias, "tag_id", "crm_tag", "id", "crm_tag"
                )
                self.env.cr.execute(
                    query.select(
                        SQL("%s AS lead_id", SQL.identifier(table, "id")),
                        SQL("%s AS tag_id", SQL.identifier(tag_alias, "id")),
                    )
                )
                tag_results = self.env.cr.dictfetchall()
            else:
                tag_results = []

            for lead in lead_results:
                lead_values = []
                for field in pls_fields + ["probability"]:
                    value = lead[field]
                    if field == "team_id":
                        continue
                    if value or field == "probability":
                        lead_values.append((field, value))
                    elif field in ("email_state", "phone_state"):
                        lead_values.append((field, False))
                    leads_values_dict[lead["id"]] = {
                        "values": lead_values,
                        "team_id": lead["team_id"] or 0,
                    }

            for tag in tag_results:
                if tag["tag_id"]:
                    leads_values_dict[tag["lead_id"]]["values"].append(
                        ("tag_id", tag["tag_id"])
                    )
            return leads_values_dict
        else:
            for lead in self:
                lead_values = []
                for field in pls_fields:
                    if field == "team_id":
                        continue
                    value = (
                        lead[field].id
                        if isinstance(lead[field], models.BaseModel)
                        else lead[field]
                    )
                    if value or field in ("email_state", "phone_state"):
                        lead_values.append((field, value))
                if use_tags:
                    for tag in lead.tag_ids:
                        lead_values.append(("tag_id", tag.id))
                leads_values_dict[lead.id] = {
                    "values": lead_values,
                    "team_id": lead["team_id"].id,
                }
            return leads_values_dict

    def update_and_get_pls_tooltip_data(self):
        self.check_singleton()
        _unused, tooltip_data = self._pls_get_naive_bayes_probabilities(is_tooltip=True)
        sorted_scores_with_name = []

        for score, field, value in sorted(tooltip_data["scores"]):
            if field in ["phone_state", "email_state"]:
                if (
                    value in [False, "incorrect"]
                    and tools.float_compare(score, 0.50, 2) > 0
                ):
                    continue
                if value == "correct" and tools.float_compare(score, 0.50, 2) < 0:
                    continue
            if field == "tag_id":
                tag = self.tag_ids.filtered(lambda tag: tag.id == value)
                sorted_scores_with_name.append(
                    (score, field, tag.display_name, tag.color)
                )
            elif isinstance(self[field], models.BaseModel):
                sorted_scores_with_name.append(
                    (score, field, self[field].display_name, False)
                )
            else:
                sorted_scores_with_name.append((score, field, str(value), False))

        probability_values = {"automated_probability": tooltip_data["probability"]}
        if self.is_automated_probability:
            probability_values["probability"] = tooltip_data["probability"]
        self.write(probability_values)

        if tools.float_is_zero(tooltip_data["probability"], 2):
            sorted_scores_with_name = [
                (0.1, "email_state", False, False),
                (0.2, "tag_id", _("Exploration"), 4),
                (0.3, "stage_id", _("New"), False),
                (0.7, "phone_state", "correct", False),
                (0.8, "country_id", _("Belgium"), False),
                (0.9, "tag_id", _("Consulting"), 3),
            ]

        return {
            "low_3_data": [
                {"field": element[1], "value": element[2], "color": element[3]}
                for element in sorted_scores_with_name[:3]
                if tools.float_compare(element[0], 0.50, 2) < 0
            ],
            "probability": tooltip_data["probability"],
            "team_name": self.team_id.display_name,
            "top_3_data": [
                {"field": element[1], "value": element[2], "color": element[3]}
                for element in sorted_scores_with_name[::-1][:3]
                if tools.float_compare(element[0], 0.50, 2) > 0
            ],
        }
