import { fields, Record } from "@mail/core/common/record";
import { assignDefined } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";

import { FileModelMixin } from "@web/core/file_viewer/file_model";
import { _t } from "@web/core/l10n/translation";

import { loadPDFJSAssets } from "@web/core/utils/pdfjs";

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
    /** @type {string} */
    raw_access_token;
    res_name;
    message = fields.One("mail.message", { inverse: "attachment_ids" });
    create_date = fields.Datetime();
    _thumbnail;

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

    async generatePdfThumbnail() {
        await loadPDFJSAssets();
        const initialWorkerSrc = globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc;
        globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc =
            "/web/static/lib/pdfjs/build/pdf.worker.js";
        const pdf = await globalThis.pdfjsLib.getDocument(this.urlRoute).promise;
        const page = await pdf.getPage(1);
        const viewPort = page.getViewport({ scale: 1 });
        const canvas = document.createElement("canvas");
        canvas.width = 38;
        canvas.height = 38;
        const scale = canvas.width / viewPort.width;
        await page.render({
            canvasContext: canvas.getContext("2d"),
            viewport: page.getViewport({ scale }),
        }).promise;
        globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc = initialWorkerSrc;
        const thumbnail = canvas.toDataURL("image/jpeg");
        await rpc(`/mail/message/thumbnail`, {
            attachment_id: this.id,
            thumbnail: thumbnail.replace("data:image/jpeg;base64,", ""),
        });
        return thumbnail;
    }

    get gthumbnail() {
        if (this.isPdf && !this._thumbnail) {
            this.generatePdfThumbnail().then(thumb => this._thumbnail = thumb);
        }
        return this._thumbnail;
    }
}

Attachment.register();
