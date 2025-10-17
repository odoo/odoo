import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { models, fields, Command, makeKwArgs } from "@web/../tests/web_test_helpers";

export class MailCustomMessageSubtype extends models.Model {
    _name = "mail.custom.message.subtype";

    model = fields.Char();
    name = fields.Char({ required: true });
    field_tracked = fields.Char({ string: "Tracked Field", required: true });
    value_update = fields.Char();
    domain = fields.Char();
    default = fields.Boolean({ string: "Default Notification", default: true });

    create_subtype_with_options() {
        const subtype = this.env["mail.message.subtype"].create({
            name: this.name,
            description: this.name,
            field_tracked: this.field_tracked,
            value_update: this.value_update,
            domain: this.domain,
            default: this.default,
            user_ids: [Command.link(this.env.user.id)],
        });
        return {
            type: "ir.actions.act_window_close",
            infos: {
                store_data: new mailDataHelpers.Store(
                    this.browse(subtype.id),
                    makeKwArgs({ fields: ["name", "field_tracked"] })
                ).get_result(),
                subtype_id: subtype.id,
            },
        };
    }
}
