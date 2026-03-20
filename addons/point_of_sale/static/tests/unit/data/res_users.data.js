import { ResUsers as MailResUsers } from "@mail/../tests/mock_server/mock_models/res_users";

export class ResUsers extends MailResUsers {
    _name = "res.users";

    _load_pos_data_fields() {
        return ["id", "name", "partner_id", "all_group_ids"];
    }

    _records = [
        ...MailResUsers.prototype.constructor._records,
        {
            id: 2,
            name: "Administrator",
            partner_id: 3,
            role: "manager",
        },
        {
            id: 3,
            name: "User1",
            partner_id: 4,
            role: "cashier",
        },
    ];

    _post_read_pos_data(records) {
        records.forEach((user) => {
            if (user.id === 2) {
                user._role = "manager";
            } else {
                user._role = "cashier";
            }
        });
        return records;
    }
}
