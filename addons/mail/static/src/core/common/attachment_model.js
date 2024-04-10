import { Record } from "@mail/core/common/record";
import { assignDefined, rpcWithEnv } from "@mail/utils/common/misc";

import { FileModelMixin } from "@web/core/file_viewer/file_model";

let rpc;
export class Attachment extends FileModelMixin(Record) {
    static id = "id";
    /** @type {Object.<number, import("models").Attachment>} */
    static records = {};
    /** @returns {import("models").Attachment} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Attachment|import("models").Attachment[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static new(data) {
        rpc = rpcWithEnv(this.store.env);
        /** @type {import("models").Attachment} */
        const attachment = super.new(data);
        Record.onChange(attachment, ["extension", "name"], () => {
            if (!attachment.extension && attachment.name) {
                attachment.extension = attachment.name.split(".").pop();
            }
        });
        return attachment;
    }

    thread = Record.one("Thread", { inverse: "attachments" });
    res_name;
    message = Record.one("Message");
    /** @type {luxon.DateTime} */
    create_date = Record.attr(undefined, { type: "datetime" });

    get isDeletable() {
        return true;
    }

    get monthYear() {
        if (!this.create_date) {
            return undefined;
        }
        return `${this.create_date.monthLong}, ${this.create_date.year}`;
    }

    /** Remove the given attachment globally. */
    delete() {
        if (this.tmpUrl) {
            URL.revokeObjectURL(this.tmpUrl);
        }
        super.delete();
    }

    /**
     * Delete the given attachment on the server as well as removing it
     * globally.
     */
    async remove() {
        if (this.id > 0) {
            await rpc(
                "/mail/attachment/delete",
                assignDefined({ attachment_id: this.id }, { access_token: this.accessToken })
            );
        }
        this.delete();
    }
}

Attachment.register();
