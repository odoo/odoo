import { ResUsers as MailResUsers } from "@mail/../tests/mock_server/mock_models/res_users";

export class ResUsers extends MailResUsers {
    _name = "res.users";

    _load_pos_data_fields() {
        return ["id", "name", "partner_id", "all_group_ids"];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        ...MailResUsers.prototype.constructor._records,
        {
            id: 2,
            name: "Administrator",
            partner_id: 3,
            role: "manager",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 3,
            name: "User1",
            partner_id: 4,
            role: "cashier",
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
