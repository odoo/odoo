import { mailModels } from "@mail/../tests/mail_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    _load_pos_data_fields() {
        return ["id", "name", "partner_id", "all_group_ids"];
    }

    _records = [
        ...mailModels.ResUsers._records,
        {
            id: 2,
            name: "Administrator",
            partner_id: 3,
            role: "group_system",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 3,
            name: "User1",
            partner_id: 4,
            role: "regular_user",
            write_date: "2025-01-01 10:00:00",
        },
    ];

    _load_pos_data_read(records) {
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
