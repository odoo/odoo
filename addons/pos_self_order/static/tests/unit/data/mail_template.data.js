import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { MailTemplate as MailMailTemplate } from "@mail/../tests/mock_server/mock_models/mail_template";

export class MailTemplate extends MailMailTemplate {
    _name = "mail.template";

    _load_pos_data_fields() {
        return ["id"];
    }

    _records = [
        {
            id: 10,
            name: "Self-out: Conformation order",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, MailTemplate]);
