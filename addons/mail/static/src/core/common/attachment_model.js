/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { onChange } from "@mail/utils/common/misc";

import { deserializeDateTime } from "@web/core/l10n/dates";
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
        onChange(attachment, ["extension", "name"], () => {
            if (!attachment.extension && attachment.name) {
                attachment.extension = attachment.name.split(".").pop();
            }
        });
        return attachment;
    }

    update(data) {
        super.update(data);
        this.originThread?.attachments.sort((a1, a2) => (a1.id < a2.id ? 1 : -1));
    }

    originThread = Record.one("Thread", { inverse: "attachments" });
    res_name;
    message = Record.one("Message");
    /** @type {string} */
    create_date;

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
