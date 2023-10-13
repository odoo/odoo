/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";

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
    /**
     * @param {Object} data
     * @returns {import("models").Attachment}
     */
    static insert(data) {
        if (!("id" in data)) {
            throw new Error("Cannot insert attachment: id is missing in data");
        }
        /** @type {import("models").Attachment} */
        const attachment = this.preinsert(data);
        attachment.update(data);
        return attachment;
    }

    update(data) {
        assignDefined(this, data, [
            "checksum",
            "create_date",
            "filename",
            "mimetype",
            "name",
            "type",
            "url",
            "uploading",
            "extension",
            "accessToken",
            "tmpUrl",
            "message",
            "res_name",
        ]);
        if (!("extension" in data) && data["name"]) {
            this.extension = this.name.split(".").pop();
        }
        if (data.originThread !== undefined) {
            const threadData = Array.isArray(data.originThread)
                ? data.originThread[0][1]
                : data.originThread;
            this.originThread = {
                model: threadData.model,
                id: threadData.id,
            };
            const thread = this.originThread;
            thread.attachments.add(this);
            thread.attachments.sort((a1, a2) => (a1.id < a2.id ? 1 : -1));
        }
    }

    originThread = Record.one("Thread");
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
