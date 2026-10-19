import { fields, models } from "@web/../tests/web_test_helpers";


export class CrmTeam extends models.ServerModel {
    _name = "crm.team";

    name = fields.Char();
    member_ids = fields.Many2many({ string: "Salespersons", relation: "res.users" });
    is_membership_multi = fields.Boolean({ default: false });
    member_warning = fields.Text({ compute: "_compute_member_warning" });

    _compute_member_warning() {
        for (const team of this) {
            const other_memberships = this.env["crm.team"].search_count([
                ["id", "!=", team.id],
                ["member_ids", "in", team.member_ids]
            ]);
            team.member_warning = other_memberships ? "Users already in other teams." : false;
        }
    }
}
