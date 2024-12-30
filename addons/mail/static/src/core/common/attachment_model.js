import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";

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
    static new() {
        /** @type {import("models").Attachment} */
        const attachment = super.new(...arguments);
        Record.onChange(attachment, ["extension", "filename"], () => {
            if (!attachment.extension && attachment.filename) {
                attachment.extension = attachment.filename.split(".").pop();
            }
        });
        return attachment;
    }

    thread = Record.one("Thread", { inverse: "attachments" });
    res_name;
    message = Record.one("Message", { inverse: "attachment_ids" });
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

    get uploading() {
        return this.id < 0;
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
            const rpcParams = assignDefined(
                { attachment_id: this.id },
                { access_token: this.access_token }
            );
            const thread = this.thread || this.message?.thread;
            if (thread) {
                Object.assign(rpcParams, thread.rpcParams);
            }
            await rpc("/mail/attachment/delete", rpcParams);
        }
        this.delete();
    }
}

Attachment.register();
