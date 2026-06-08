import { fields, Record } from "@mail/model/export";
import { assignDefined } from "@mail/utils/common/misc";
import { generatePdfThumbnail } from "@web/core/utils/pdfjs";

import { FileModelMixin } from "@web/core/file_viewer/file_model";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { imageUrl, url } from "@web/core/utils/urls";

export class Attachment extends FileModelMixin(Record) {
    static _name = "ir.attachment";
    static new() {
        /** @type {import("models").Attachment} */
        const attachment = super.new(...arguments);
        attachment.registerRecordOnChange(attachment, ["extension", "name"], () => {
            if (!attachment.extension && attachment.name) {
                attachment.extension = attachment.name.split(".").pop();
            }
        });
        return attachment;
    }

    composer = fields.One("Composer", { inverse: "attachments" });
    thread = fields.One("mail.thread", { inverse: "attachments" });
    /** @type {string} */
    raw_access_token;
    res_name;
    /** @type {string} */
    thumbnail_access_token;
    message = fields.One("mail.message", { inverse: "attachment_ids" });
    /** @type {string} */
    ownership_token;
    create_date = fields.Datetime();
    has_thumbnail = fields.Attr(undefined, {
        onUpdate() {
            if (
                (this.isPdf || this.isVideo) &&
                !this.has_thumbnail &&
                (this.ownership_token ||
                    // If related to a record, must have write access to it
                    ((!this.thread || this.thread.hasWriteAccess) &&
                        this.store.self_user?.share === false))
            ) {
                this.setThumbnail();
            }
        },
    });
    get thumbnailUrl() {
        const params = assignDefined(
            {},
            {
                access_token: this.thumbnail_access_token,
                crop: "top",
                unique: this.checksum,
            }
        );
        // We don't force the size for video thumbnail to not alter the aspect
        // ratio
        if (this.isPdf) {
            params.width = 180;
            params.height = 110;
        }
        return imageUrl("ir.attachment", this.id, "thumbnail", params);
    }
    generateVideoThumbnail() {
        return new Promise((resolve) => {
            const video = document.createElement("video");
            video.preload = "metadata";
            video.src = this.defaultSource;
            video.addEventListener(
                "loadedmetadata",
                () => {
                    const thumbnailCanvas = document.createElement("canvas");
                    const ratio = Math.min(320 / video.videoWidth, 196 / video.videoHeight);
                    const width = video.videoWidth * ratio;
                    const height = video.videoHeight * ratio;
                    thumbnailCanvas.width = width;
                    thumbnailCanvas.height = height;
                    video.currentTime = video.duration / 2;
                    video.addEventListener(
                        "seeked",
                        () => {
                            thumbnailCanvas
                                .getContext("2d")
                                .drawImage(
                                    video,
                                    0,
                                    0,
                                    video.videoWidth,
                                    video.videoHeight,
                                    0,
                                    0,
                                    width,
                                    height
                                );
                            const thumbnail = thumbnailCanvas
                                .toDataURL("image/jpeg")
                                .replace("data:image/jpeg;base64,", "");
                            resolve(thumbnail);
                        },
                        { once: true }
                    );
                },
                { once: true }
            );
        });
    }

    get gifPaused() {
        return this.thread ? !this.thread.isFocused : !this.composer?.isFocused;
    }

    get isDeletable() {
        if (this.message && this.store.self_user?.share !== false) {
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

    async setThumbnail() {
        let thumbnail;
        if (this.isPdf) {
            const pdfThumbnail = await generatePdfThumbnail(
                url(
                    `/mail/attachment/pdf_first_page/${this.id}`,
                    assignDefined({}, { access_token: this.ownership_token })
                )
            );
            thumbnail = pdfThumbnail.thumbnail;
        }
        if (this.isVideo) {
            thumbnail = await this.generateVideoThumbnail();
        }
        if (thumbnail) {
            rpc(
                `/mail/attachment/update_thumbnail`,
                assignDefined(
                    { attachment_id: this.id, thumbnail },
                    { access_token: this.ownership_token }
                )
            );
        }
    }
}

Attachment.register();
