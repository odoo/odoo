/* @odoo-module */

import { Record } from "@mail/core/common/record";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { FileModelMixin } from "@web/core/file_viewer/file_model";
import { rpc } from "@web/core/network/rpc";
import { assignDefined } from "@mail/utils/common/misc";

export class Attachment extends FileModelMixin(Record) {
    static id = [["id!"], ["uploadId!"]];
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

    uploadId;
    originThread = Record.one("Thread", { inverse: "attachments" });
    res_name;
    message = Record.one("Message");
    /** @type {string} */
    create_date;
    /** @type {Deferred} */
    uploadDoneDeferred;
    /** @type {() => void} */
    uploadAbort;
    uploadHooker;

    /** Delete the given attachment on the server as well as removing it globally. */
    async unlink() {
        if (this.uploadAbort) {
            this.uploadAbort();
            this.uploadDoneDeferred.resolve();
        }
        if (this.id) {
            await rpc(
                "/mail/attachment/delete",
                assignDefined({ attachment_id: this.id }, { access_token: this.accessToken })
            );
        }
        this.delete();
    }

    delete() {
        if (this.tmpUrl) {
            URL.revokeObjectURL(this.tmpUrl);
        }
        if (this._store.env.services["discuss.voice_message"] && this.voice && this.id) {
            this._store.env.services["discuss.voice_message"].activePlayer = null;
        }
        super.delete();
    }

    get isDeletable() {
        return true;
    }

    get monthYear() {
        if (!this.create_date) {
            return undefined;
        }
        const datetime = deserializeDateTime(this.create_date);
        return `${datetime.monthLong}, ${datetime.year}`;
    }
}

Attachment.register();
