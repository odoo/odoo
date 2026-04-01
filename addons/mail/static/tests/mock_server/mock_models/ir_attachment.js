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
    _to_store(store, fields) {
        const kwargs = getKwArgs(arguments, "store", "fields");
        fields = kwargs.fields;

        for (const attachment of this) {
            const [data] = this._read_format(
                attachment.id,
                fields.filter((field) => field !== "thread"),
                false
            );
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
            store._add_record_fields(this.browse(attachment.id), data);
        }
    }

    get _to_store_defaults() {
        return [
            "checksum",
            "create_date",
            "mimetype",
            "name",
            "res_name",
            "thread",
            "type",
            "url",
            "voice_ids",
        ];
    }
}
