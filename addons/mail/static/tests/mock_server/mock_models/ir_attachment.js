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
    _attachment_format(ids) {
        /** @type {import("mock_models").DiscussVoiceMetadata} */
        const DiscussVoiceMetadata = this.env["discuss.voice.metadata"];

        return this.read(ids).map((attachment) => {
            const res = {
                create_date: attachment.create_date,
                checksum: attachment.checksum,
                filename: attachment.name,
                id: attachment.id,
                mimetype: attachment.mimetype,
                name: attachment.name,
                size: attachment.file_size,
            };
            res["thread"] = [["ADD", { id: attachment.res_id, model: attachment.res_model }]];
            const voice = DiscussVoiceMetadata._filter([["attachment_id", "=", attachment.id]])[0];
            if (voice) {
                res.voice = true;
            }
            return res;
        });
    }
}
