import { fields, Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";

import { FileModelMixin } from "@web/core/file_viewer/file_model";
import { _t } from "@web/core/l10n/translation";

export class Attachment extends FileModelMixin(Record) {
    static _name = "ir.attachment";
    static id = "id";
    static new() {
        /** @type {import("models").Attachment} */
        const attachment = super.new(...arguments);
        Record.onChange(attachment, ["extension", "name"], () => {
            if (!attachment.extension && attachment.name) {
                attachment.extension = attachment.name.split(".").pop();
            }
        });
        return attachment;
    }

    thread = fields.One("Thread", { inverse: "attachments" });
    res_name;
    message = fields.One("mail.message", { inverse: "attachment_ids" });
    create_date = fields.Datetime();

    get isDeletable() {
        if (this.message && !this.store.self.isInternalUser) {
            return this.message.editable;
        }
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

    get previewName() {
        return this.voice ? _t("Voice Message") : this.name || "";
    }
}

Attachment.register();
