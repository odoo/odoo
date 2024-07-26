import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { getKwArgs, makeKwArgs, webModels } from "@web/../tests/web_test_helpers";

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

        const [attachment] = this.browse(ids);
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
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;

        /** @type {import("mock_models").DiscussVoiceMetadata} */
        const DiscussVoiceMetadata = this.env["discuss.voice.metadata"];

        if (!fields) {
            fields = [
                "checksum",
                "create_date",
                "filename",
                "mimetype",
                "name",
                "res_name",
                "size",
                "thread",
            ];
        }

        for (const attachment of this.browse(ids)) {
            const [data] = this.read(
                attachment.id,
                fields.filter((field) => !["filename", "size", "thread"].includes(field)),
                makeKwArgs({ load: false })
            );
            if (fields.includes("filename")) {
                data.filename = attachment.name;
            }
            if (fields.includes("size")) {
                data.size = attachment.file_size;
            }
            if (fields.includes("thread")) {
                data.thread =
                    attachment.model !== "mail.compose.message" && attachment.res_id
                        ? mailDataHelpers.Store.one(
                              this.env[attachment.res_model].browse(attachment.res_id),
                              makeKwArgs({
                                  as_thread: true,
                                  only_id: true,
                              })
                          )
                        : false;
            }
            const voice = DiscussVoiceMetadata.browse(attachment.id)[0];
            if (voice) {
                data.voice = true;
            }
            store.add(this.browse(attachment.id), data);
        }
    }
}
