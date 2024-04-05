import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

import { FileModelMixin } from "@web/core/file_viewer/file_model";

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

    /**
     * Delete the given attachment on the server as well as removing it
     * globally.
     */
    async fullyRemove() {
        this.remove();
        if (this.id > 0) {
            await this.rpc(
                "/mail/attachment/delete",
                assignDefined({ attachment_id: this.id }, { access_token: this.accessToken })
            );
        }
    }

    /** Remove the given attachment globally. */
    remove() {
        if (this.tmpUrl) {
            URL.revokeObjectURL(this.tmpUrl);
        }
        this.delete();
    }
}

Attachment.register();
