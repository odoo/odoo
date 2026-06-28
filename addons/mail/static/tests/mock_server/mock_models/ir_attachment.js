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

    _store_ownership_fields(res) {
        res.attr("ownership_token", (a) => a.id); // mock: token is the record id
    }

    _store_attachment_fields(res) {
        res.extend(["checksum", "create_date", "file_size", "has_thumbnail", "mimetype", "name"]);
        res.attr("raw_access_token", (a) => a.id); // mock: token is the record id
        res.attr("res_name");
        res.attr("res_model");
        res.one("thread", [], { as_thread: true });
        res.attr("thumbnail_access_token", (a) => a.id); // mock: token is the record id
        res.extend(["type", "url"]);
        // sudo: discuss.voice.metadata - checking the existence of voice metadata is acceptable
        res.many("voice_ids", [], { sudo: true });
    }
}
