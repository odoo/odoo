from psycopg.errors import UniqueViolation

from odoo import _, api, exceptions, fields, models


# Each tree contains nodes arranged with prerequisite edges.  Users
# unlock nodes by completing linked quests or challenges, giving a
# visual map of "what's possible" and "what I've achieved."  This maps
# to Octalysis drives 2 (Accomplishment), 3 (Creativity/Choice), and
# 4 (Ownership).
class GamificationSkillTree(models.Model):
    """Branching skill progression tree (e.g., Sales, Technical, Leadership)."""

    _name = "gamification.skill.tree"
    _description = "Gamification Skill Tree"
    _order = "sequence, name"

    name = fields.Char(
        string="Tree Name",
        translate=True,
        required=True,
    )
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    icon = fields.Image(
        max_width=128,
        max_height=128,
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )

    node_ids = fields.One2many(
        comodel_name="gamification.skill.node",
        inverse_name="tree_id",
        string="Nodes",
    )
    node_count = fields.Count(
        count_of="node_ids",
        string="# Nodes",
    )


# Nodes represent specific skills or competencies.  They can be
# unlocked by completing associated quests or meeting karma thresholds.
# Prerequisite edges between nodes create the branching tree structure.
class GamificationSkillNode(models.Model):
    """Individual competency node within a skill tree."""

    _name = "gamification.skill.node"
    _description = "Skill Tree Node"
    _order = "tree_id, level, sequence"

    name = fields.Char(
        string="Skill Name",
        translate=True,
        required=True,
    )
    description = fields.Text(translate=True)
    tree_id = fields.Many2one(
        comodel_name="gamification.skill.tree",
        string="Skill Tree",
        index=True,
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    level = fields.Integer(
        string="Tree Level",
        default=1,
        help="Vertical position in the tree (1 = root, higher = deeper).",
    )

    # Prerequisites
    prerequisite_ids = fields.Many2many(
        comodel_name="gamification.skill.node",
        relation="gamification_skill_node_prereq_rel",
        column1="node_id",
        column2="prereq_id",
        string="Prerequisites",
        domain="[('tree_id', '=', tree_id), ('id', '!=', id)]",
    )
    dependent_ids = fields.Many2many(
        comodel_name="gamification.skill.node",
        relation="gamification_skill_node_prereq_rel",
        column1="prereq_id",
        column2="node_id",
        string="Unlocked By This",
        readonly=True,
    )

    # Unlock conditions
    karma_threshold = fields.Integer(
        default=0,
        help="Minimum karma required to unlock (0 = no karma requirement).",
    )
    quest_id = fields.Many2one(
        comodel_name="gamification.quest",
        string="Required Quest",
        ondelete="set null",
        help="Quest that must be completed to unlock this node.",
    )

    # Rewards
    karma_reward = fields.Integer(
        string="Unlock Karma",
        default=0,
    )
    badge_id = fields.Many2one(
        comodel_name="gamification.badge",
        string="Unlock Badge",
        ondelete="set null",
    )

    # Tracking
    unlock_ids = fields.One2many(
        comodel_name="gamification.skill.node.unlock",
        inverse_name="node_id",
        string="Unlocks",
    )
    unlock_count = fields.Count(
        count_of="unlock_ids",
        string="# Unlocked",
    )

    def check_unlock_for_user(self, user):
        """Check if a user meets the conditions to unlock this node.

        :param user: ``res.users`` record.
        :return: True if all conditions are met.
        """
        self.check_singleton()
        Unlock = self.env["gamification.skill.node.unlock"]

        # Already unlocked?
        if Unlock.search_count(
            [
                ("node_id", "=", self.id),
                ("user_id", "=", user.id),
            ],
            limit=1,
        ):
            return False

        # Check prerequisites — single query for all prereqs
        if self.prerequisite_ids:
            unlocked_prereqs = Unlock.search(
                [
                    ("node_id", "in", self.prerequisite_ids.ids),
                    ("user_id", "=", user.id),
                ]
            ).mapped("node_id")
            if self.prerequisite_ids - unlocked_prereqs:
                return False

        # Check karma threshold
        if self.karma_threshold and user.karma < self.karma_threshold:
            return False

        # Check quest completion
        if self.quest_id:
            completed = self.env["gamification.quest.enrollment"].search_count(
                [
                    ("quest_id", "=", self.quest_id.id),
                    ("user_id", "=", user.id),
                    ("state", "=", "completed"),
                ]
            )
            if not completed:
                return False

        return True

    def unlock_for_user(self, user):
        """Unlock this node for a user, granting rewards and cascading.

        Unlocking a node can satisfy the last missing prerequisite of a
        dependent node, so after granting we retry the newly-reachable
        dependents (bounded by the tree, which is acyclic — see
        ``_check_no_prerequisite_cycle``).

        Runs as ``sudo`` throughout: the unlock, the karma grant, the badge and
        the activity row are all system-awarded, and ``base.group_user`` has no
        write access to ``gamification.skill.node.unlock``.  The unique index
        makes it race-safe — a concurrent unlock raises inside the savepoint
        and is treated as "already unlocked" rather than aborting the caller.

        :param user: ``res.users`` record.
        :return: created unlock record, or ``False`` if conditions not met or
            it was unlocked concurrently.
        """
        self.check_singleton()
        if not self.check_unlock_for_user(user):
            return False

        Unlock = self.env["gamification.skill.node.unlock"].sudo()
        try:
            with self.env.cr.savepoint():
                unlock = Unlock.create(
                    {
                        "node_id": self.id,
                        "user_id": user.id,
                    }
                )
        except UniqueViolation:
            # Lost the race on the (user_id, node_id) unique index.  Narrow on
            # purpose: `except Exception` here reported every failure, including
            # access errors and plain bugs, as "already unlocked".
            return False

        # Grant rewards
        if self.karma_reward:
            user.sudo()._add_karma(
                self.karma_reward,
                source=unlock,
                reason=_("Skill unlocked: %s", self.name),
            )
        if self.badge_id:
            self.env["gamification.badge.user"].sudo().create(
                {
                    "user_id": user.id,
                    "badge_id": self.badge_id.id,
                }
            )._send_badge()

        self.env["gamification.activity"]._log_skill_unlocked(
            user, self, self.karma_reward
        )

        return unlock

    @api.model
    def _unlock_nodes_for_quest(self, enrollment):
        """Unlock skill nodes reachable after a quest the user completed.

        This is the link the data model declares (``node.quest_id``) but that
        nothing consumed, leaving the skill tree inert.  Completing the quest
        unlocks the directly-gated nodes and then re-scans their trees to a
        fixpoint, so a node whose *only* remaining requirement was a
        prerequisite that just unlocked also opens — while a node with its own
        unmet karma threshold or quest stays locked (``check_unlock_for_user``
        is re-evaluated for each candidate).

        The cascade lives here rather than in ``unlock_for_user`` on purpose:
        unlocking a single node is an atomic, non-cascading operation (a caller
        that unlocks one node must not implicitly unlock half its tree).

        The walk follows prerequisite edges *downstream from the quest-gated
        seed only* — it will not open an unrelated free-standing node elsewhere
        in the tree just because a quest in that tree completed.  The
        prerequisite graph is acyclic (``_check_no_prerequisite_cycle``), so
        the frontier is finite.
        """
        user = enrollment.user_id
        frontier = self.search([("quest_id", "=", enrollment.quest_id.id)])
        while frontier:
            next_frontier = self.browse()
            for node in frontier:
                if node.unlock_for_user(user):
                    # Its dependents may now be reachable — visit them next.
                    next_frontier |= node.dependent_ids
            frontier = next_frontier

    @api.model
    def _cron_check_skill_unlocks(self):
        """Unlock nodes whose conditions a user now meets.

        ``check_unlock_for_user`` honours ``karma_threshold``, but its only
        caller was ``_unlock_nodes_for_quest``, seeded from
        ``search([("quest_id", "=", ...)])``.  A node gated on karma alone --
        or on a prerequisite that a karma-gated node unlocks -- could therefore
        never open, because nothing ever asked.  This asks, nightly.

        Scoped to nodes that *can* open on karma: a node with no threshold and
        no quest is either already reachable through its prerequisites or has no
        condition to meet, and a quest-gated one is handled at completion.
        """
        candidates = self.search([("karma_threshold", ">", 0)])
        if not candidates:
            return
        users = self.env["res.users"].search(
            [
                ("active", "=", True),
                ("share", "=", False),
                ("karma", ">=", min(candidates.mapped("karma_threshold"))),
            ]
        )
        for node in candidates:
            for user in users.filtered(lambda u, n=node: u.karma >= n.karma_threshold):
                # Each unlock can satisfy the last missing prerequisite of a
                # dependent, so walk the same frontier the quest path walks.
                frontier = node
                while frontier:
                    opened = frontier.browse()
                    for candidate in frontier:
                        if candidate.unlock_for_user(user):
                            opened |= candidate.dependent_ids
                    frontier = opened

    @api.constrains("prerequisite_ids")
    def _check_no_prerequisite_cycle(self):
        """Reject a node that is its own (in)direct prerequisite.

        A cycle would deadlock ``check_unlock_for_user`` — every node in the
        loop waits on another that can never unlock first — and could loop the
        ``unlock_for_user`` cascade.  Detected with an iterative closure over
        the prerequisite edges.
        """
        for node in self:
            seen = set()
            frontier = node.prerequisite_ids
            while frontier:
                if node in frontier:
                    raise exceptions.ValidationError(
                        _(
                            "Skill node %s cannot be a prerequisite of itself "
                            "(directly or transitively).",
                            node.name,
                        )
                    )
                seen |= set(frontier.ids)
                frontier = frontier.prerequisite_ids.filtered(
                    lambda n, seen=seen: n.id not in seen
                )


class GamificationSkillNodeUnlock(models.Model):
    """Record of a user unlocking a skill tree node."""

    _name = "gamification.skill.node.unlock"
    _description = "Skill Node Unlock"
    _order = "unlock_date desc"

    node_id = fields.Many2one(
        comodel_name="gamification.skill.node",
        index=True,
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        ondelete="cascade",
    )
    unlock_date = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
    )

    _user_node_uniq = models.UniqueIndex(
        "(user_id, node_id)",
        "A user can only unlock a skill node once.",
    )
