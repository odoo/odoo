import { fields, models } from "@web/../tests/web_test_helpers";

export class TeamTeam extends models.ServerModel {
    _name = "team.team";

    name = fields.Char();
    member_ids = fields.Many2many({ string: "Members", relation: "res.users" });
    is_membership_multi = fields.Boolean({ default: false });
    can_activate_multi_membership = fields.Boolean({ default: true });
    member_warning = fields.Text({ compute: "_compute_member_warning" });

    _compute_member_warning() {
        for (const team of this) {
            const other_memberships = this.env["team.team"].search_count([
                ["id", "!=", team.id],
                ["member_ids", "in", team.member_ids],
            ]);
            team.member_warning = other_memberships
                ? "Users already in other teams."
                : false;
        }
    }
}
