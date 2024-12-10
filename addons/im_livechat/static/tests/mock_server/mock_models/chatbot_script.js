import { getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

export class ChatbotScript extends models.ServerModel {
    _name = "chatbot.script";

    /** @param {number[]} ids */
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields ?? ["title", "operator_partner_id"];
        for (const script of this.browse(ids)) {
            const [data] = this._read_format(
                script.id,
                fields.filter((field) => "operator_partner_id" !== field),
                false
            );
            if (fields.includes("operator_partner_id")) {
                data["operator_partner_id"] = mailDataHelpers.Store.one(
                    this.env["res.partner"].browse(script.operator_partner_id),
                    makeKwArgs({ fields: ["name"] })
                );
            }
            store.add(this.browse(script.id), data);
        }
    }
}
