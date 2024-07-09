import { getKwArgs, webModels } from "@web/../tests/web_test_helpers";

export class IrAttachment extends webModels.IrAttachment {
    /**
     * @param {number} ids
     * @param {boolean} [force]
     */
    register_as_main_attachment(ids, force) {
        const kwargs = getKwArgs(arguments, "ids", "force");
        ids = kwargs.ids;
        delete kwargs.ids;
        force = kwargs.force ?? true;

        const [attachment] = this._filter([["id", "in", ids]]);
        if (!attachment.res_model) {
            return true; // dummy value for mock server
        }
        if (!this.env[attachment.res_model]._fields.message_main_attachment_id) {
            return true; // dummy value for mock server
        }
        const [record] = this.env[attachment.res_model].search_read([
            ["id", "=", attachment.res_id],
        ]);
        if (force || !record.message_main_attachment_id) {
            this.env[attachment.res_model].write([record.id], {
                message_main_attachment_id: attachment.id,
            });
        }
        return true; // dummy value for mock server
    }

    /** @param {number} ids */
    _to_store(ids, store) {
        /** @type {import("mock_models").DiscussVoiceMetadata} */
        const DiscussVoiceMetadata = this.env["discuss.voice.metadata"];

        for (const attachment of this.browse(ids)) {
            const res = {
                checksum: attachment.checksum,
                create_date: attachment.create_date,
                filename: attachment.name,
                id: attachment.id,
                mimetype: attachment.mimetype,
                name: attachment.name,
                size: attachment.file_size,
                thread:
                    attachment.res_id && attachment.model !== "mail.compose.message"
                        ? { id: attachment.res_id, model: attachment.res_model }
                        : false,
            };
            const voice = DiscussVoiceMetadata._filter([["attachment_id", "=", attachment.id]])[0];
            if (voice) {
                res.voice = true;
            }
            store.add("Attachment", res);
        }
    }
}
