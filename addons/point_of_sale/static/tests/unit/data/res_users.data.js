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
        },
        {
            id: 3,
            name: "User1",
            partner_id: 4,
            role: "group_user",
        },
    ];
}
