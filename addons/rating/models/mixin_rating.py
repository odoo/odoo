from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.numbers import float_compare, float_round

from odoo.addons.rating.models import rating_data


class MixinRating(models.AbstractModel):
    """This mixin adds rating statistics to mixin.mail.thread that already support ratings."""

    _name = "mixin.rating"
    _description = "Rating Mixin"
    _inherit = ["mixin.mail.thread"]

    rating_last_value = fields.Float(
        compute="_compute_rating_last_value",
        compute_sudo=True,
        store=True,
        aggregator="avg",
        groups="base.group_user",
    )
    rating_last_feedback = fields.Text(
        related="rating_ids.feedback",
        string="Rating Last Feedback",
        groups="base.group_user",
    )
    rating_last_image = fields.Binary(
        related="rating_ids.rating_image",
        string="Rating Last Image",
        groups="base.group_user",
    )
    rating_count = fields.Integer(
        string="Rating count",
        compute="_compute_rating_stats",
        compute_sudo=True,
    )
    rating_avg = fields.Float(
        string="Average Rating",
        compute="_compute_rating_stats",
        search="_search_rating_avg",
        compute_sudo=True,
        groups="base.group_user",
    )
    rating_avg_text = fields.Selection(
        selection=rating_data.RATING_TEXT,
        compute="_compute_rating_avg_text",
        compute_sudo=True,
        groups="base.group_user",
    )
    rating_percentage_satisfaction = fields.Float(
        string="Rating Satisfaction",
        compute="_compute_rating_percentage_satisfaction",
        compute_sudo=True,
    )
    rating_last_text = fields.Selection(
        related="rating_ids.rating_text",
        string="Rating Text",
        groups="base.group_user",
    )

    @api.depends("rating_ids", "rating_ids.rating", "rating_ids.consumed")
    def _compute_rating_last_value(self):
        # Pure SQL instead of calling read_group to allow ordering array_agg
        self.flush_model(["rating_ids"])
        self.env["rating.rating"].flush_model(["consumed", "rating"])
        if not self.ids:
            self.rating_last_value = 0
            return
        self.env.cr.execute(
            """
            SELECT
                array_agg(rating ORDER BY write_date DESC, id DESC) AS "ratings",
                res_id as res_id
            FROM "rating_rating"
            WHERE
                res_model = %s
            AND res_id = ANY(%s)
            AND consumed = true
            GROUP BY res_id""",
            [self._name, list(self.ids)],
        )
        read_group_raw = self.env.cr.dictfetchall()
        rating_by_res_id = {e["res_id"]: e["ratings"][0] for e in read_group_raw}
        for record in self:
            record.rating_last_value = rating_by_res_id.get(record.id, 0)

    @api.depends("rating_ids.res_id", "rating_ids.rating")
    def _compute_rating_stats(self):
        """Compute avg and count in one query, as thoses fields will be used together most of the time."""
        domain = self._get_domain_rating() & Domain(
            "rating", ">=", rating_data.RATING_LIMIT_MIN
        )
        read_group_res = self.env["rating.rating"]._read_group(
            domain, ["res_id"], aggregates=["__count", "rating:avg"]
        )  # force average on rating column
        mapping = {
            res_id: {"rating_count": count, "rating_avg": rating_avg}
            for res_id, count, rating_avg in read_group_res
        }
        for record in self:
            record.rating_count = mapping.get(record.id, {}).get("rating_count", 0)
            record.rating_avg = mapping.get(record.id, {}).get("rating_avg", 0)

    def _search_rating_avg(self, operator, value):
        op = rating_data.OPERATOR_MAPPING.get(operator)
        if not op:
            return NotImplemented
        rating_read_group = (
            self.env["rating.rating"]
            .sudo()
            ._read_group(
                [
                    ("res_model", "=", self._name),
                    ("consumed", "=", True),
                    ("rating", ">=", rating_data.RATING_LIMIT_MIN),
                ],
                ["res_id"],
                ["rating:avg"],
            )
        )
        res_ids = [
            res_id
            for res_id, rating_avg in rating_read_group
            if op(float_compare(rating_avg, value, 2), 0)
        ]
        return [("id", "in", res_ids)]

    @api.depends("rating_avg")
    def _compute_rating_avg_text(self):
        for record in self:
            record.rating_avg_text = rating_data._rating_avg_to_text(record.rating_avg)

    @api.depends("rating_ids.res_id", "rating_ids.rating")
    def _compute_rating_percentage_satisfaction(self):
        """Compute the rating satisfaction percentage, this is done separately from rating_count and rating_avg
        since the query is different, to avoid computing if it is not necessary"""
        domain = self._get_domain_rating() & Domain(
            "rating", ">=", rating_data.RATING_LIMIT_MIN
        )
        # See `_compute_rating_percentage_satisfaction` above
        read_group_res = self.env["rating.rating"]._read_group(
            domain, ["res_id", "rating"], aggregates=["__count"]
        )
        default_grades = {"great": 0, "okay": 0, "bad": 0}
        grades_per_record = {record_id: default_grades.copy() for record_id in self.ids}

        for record_id, rating, count in read_group_res:
            grade = rating_data._rating_to_grade(rating)
            grades_per_record[record_id][grade] += count

        for record in self:
            grade_repartition = grades_per_record.get(record.id, default_grades)
            grade_count = sum(grade_repartition.values())
            record.rating_percentage_satisfaction = (
                grade_repartition["great"] * 100 / grade_count if grade_count else -1
            )

    def write(self, vals):
        """If the rated ressource name is modified, we should update the rating res_name too.
        If the rated ressource parent is changed we should update the parent_res_id too"""
        result = super().write(vals)
        records = self.sudo()  # ratings may be inaccessible
        # _rec_name only answers for the default display_name; a model that
        # overrides _compute_display_name renames on whatever that depends on,
        # and rating.res_name is stored, so it went stale on all of it
        if not self._display_name_field_names().isdisjoint(vals):
            self.env.add_to_compute(
                self.env["rating.rating"]._fields["res_name"], records.rating_ids
            )
        # both questions are about the model and the vals, not about a record:
        # asking them per record only cost a rating_ids read each time
        parent_field = self._rating_get_parent_field_name()
        if parent_field and parent_field in vals:
            for record in records:
                record.rating_ids.write({"parent_res_id": record[parent_field].id})
        return result

    def _rating_get_parent_field_name(self):
        """Return the name of the field holding the parent relation, or None."""
        return

    def _get_domain_rating(self, record_ids=None):
        """Returns a normalized domain on rating.rating to select the records to
        include in count, avg, ... computation of current model.

        :param record_ids: what to scope ``res_id`` on, defaulting to
            ``self.ids``. A ``Query`` is accepted and stays a subquery,
            which is the point: a caller that wants *every* record of the
            model would otherwise have to ``search()`` them first and hand
            back an id list that grows without bound. `im_livechat`'s
            "% of Happiness" digest KPI did exactly that -- measured at
            0.4 ms with no livechat history and 4.9 ms at 100,000 sessions,
            per read, six reads per recipient.
        """
        return Domain(
            [
                ("res_model", "=", self._name),
                ("res_id", "in", self.ids if record_ids is None else record_ids),
                ("consumed", "=", True),
            ]
        )

    def _rating_get_repartition(self, add_stats=False, domain=None, record_ids=None):
        """get the repatition of rating grade for the given res_ids.
        :param add_stats : flag to add stat to the result
        :type add_stats : boolean
        :param domain : optional extra domain of the rating to include/exclude in repartition
        :return dictionnary
            if not add_stats, the dict is like
                - key is the rating value (integer)
                - value is the number of object (res_model, res_id) having the value
            otherwise, key is the value of the information (string) : either stat name (avg, total, ...) or 'repartition'
            containing the same dict if add_stats was False.
        """
        base_domain = self._get_domain_rating(record_ids=record_ids) & Domain(
            "rating", ">=", 1
        )
        if domain:
            base_domain &= Domain(domain)
        rg_data = self.env["rating.rating"]._read_group(
            base_domain, ["rating"], ["__count"]
        )
        # init dict with all possible rate value, except 0 (no value for the rating)
        values = dict.fromkeys(range(1, 6), 0)
        for rating, count in rg_data:
            rating_val_round = float_round(rating, precision_digits=1)
            values[rating_val_round] = values.get(rating_val_round, 0) + count
        # add other stats
        if add_stats:
            rating_number = sum(values.values())
            return {
                "repartition": values,
                "avg": sum(float(key * values[key]) for key in values) / rating_number
                if rating_number > 0
                else 0,
                "total": sum(count for __, count in rg_data),
            }
        return values

    def rating_get_grades(self, domain=None, record_ids=None):
        """Get the repartitions of rating grade for the given res_ids.
        :param domain: Optional domain of the rating to include/exclude
            in the grades computation.
        :param record_ids: Optional override for which records to grade,
            passed to :meth:`_get_domain_rating`; a ``Query`` stays a subquery.
        :returns: A dictionary where the key is the grade bucket and the value
            is the count of unique ``(res_model, res_id)`` pairs whose
            grades are associated with that rating.

            The rates are:

            * ``"great"``, graded between 70 and 100
            * ``"okay"``, graded between 31 and 69
            * ``"bad"``, graded between 0 and 30
        :rtype: dict[typing.Literal["great", "okay", "bad"], int]
        """
        data = self._rating_get_repartition(domain=domain, record_ids=record_ids)
        res = dict.fromkeys(["great", "okay", "bad"], 0)
        for key in data:
            grade = rating_data._rating_to_grade(key)
            res[grade] += data[key]
        return res

    def rating_get_stats(self, domain=None):
        """Get the statistics of the rating repartitions

        :param domain : optional domain of the rating to include/exclude in statistic computation
        :returns: A dictionnary where:

            - key is the name of the information (stat name)
            - value is statistic value : 'percent' contains the repartition in percentage, 'avg' is the average rate
              and 'total' is the number of rating
        """
        data = self._rating_get_repartition(domain=domain, add_stats=True)
        result = {
            "avg": data["avg"],
            "total": data["total"],
            "percent": dict.fromkeys(range(1, 6), 0),
        }
        for rate in data["repartition"]:
            result["percent"][rate] = (
                (data["repartition"][rate] * 100) / data["total"]
                if data["total"] > 0
                else 0
            )
        return result

    def _rating_get_stats_per_record(self, domain=None):
        """
        Computes rating statistics for each record individually.

        :param domain: Optional domain to apply on the ratings.
        :return: A dictionary mapping each record ID to its statistics dictionary.
        :rtype: dict
        """
        base_domain = self._get_domain_rating() & Domain("rating", ">=", 1)
        if domain:
            base_domain &= Domain(domain)
        rg_data = self.env["rating.rating"]._read_group(
            base_domain,
            groupby=["res_id", "rating"],
            aggregates=["__count"],
        )
        stats_per_record = defaultdict(
            lambda: {
                "total": 0,
                "weighted_sum": 0.0,
                "counts": defaultdict(int),
                "percent": {},
            }
        )
        for res_id, rating, count in rg_data:
            stats = stats_per_record[res_id]
            stats["total"] += count
            stats["weighted_sum"] += rating * count
            stats["counts"][int(rating)] += count
        for stats in stats_per_record.values():
            total = stats["total"]
            if total > 0:
                stats["avg"] = stats["weighted_sum"] / total
                stats["percent"] = {
                    rate: (stats["counts"].get(rate, 0) * 100) / total
                    for rate in range(1, 6)
                }
            else:
                stats["avg"] = 0
                stats["percent"] = dict.fromkeys(range(1, 6), 0.0)
            del stats["weighted_sum"]
            del stats["counts"]
        return stats_per_record

    @api.model
    def _allow_publish_rating_stats(self):
        """Override to allow the rating stats to be demonstrated."""
        return False
