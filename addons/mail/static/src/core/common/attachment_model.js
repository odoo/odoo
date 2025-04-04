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

    composer = fields.One("Composer", { inverse: "attachments" });
    thread = fields.One("Thread", { inverse: "attachments" });
    /** @type {string} */
    raw_access_token;
    res_name;
    message = fields.One("mail.message", { inverse: "attachment_ids" });
    /** @type {string} */
    ownership_token;
    create_date = fields.Datetime();

    get gifPaused() {
        return this.thread ? !this.thread.isFocused : !this.composer?.isFocused;
    }

    get isDeletable() {
        if (this.message && this.store.self.main_user_id?.share !== false) {
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
            await rpc(
                "/mail/attachment/delete",
                assignDefined({ attachment_id: this.id }, { access_token: this.ownership_token })
            );
        }
        this.delete();
    }

    get previewName() {
        return this.voice ? _t("Voice Message") : this.name || "";
    }
}

Attachment.register();
