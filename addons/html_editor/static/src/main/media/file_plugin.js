import {
    DocumentSelector,
    renderStaticFileBox,
} from "@html_editor/main/media/media_dialog/document_selector";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

export class FilePlugin extends Plugin {
    static id = "file";
    static dependencies = ["dom", "history"];
    resources = {
        user_commands: {
            id: "uploadFile",
            title: _t("Upload a file"),
            description: _t("Add a download box"),
            icon: "fa-upload",
            run: this.uploadAndInsertFiles.bind(this),
            isAvailable: this.isUploadCommandAvailable.bind(this),
        },
        powerbox_items: {
            categoryId: "media",
            commandId: "uploadFile",
            keywords: [_t("file"), _t("document")],
        },
        unsplittable_node_predicates: (node) => node.classList?.contains("o_file_box"),
    };

    get recordInfo() {
        return this.config.getRecordInfo?.() || {};
    }

    isUploadCommandAvailable() {
        return !this.config.disableFile;
    }

    async uploadAndInsertFiles() {
        // Upload
        const attachments = await this.services.uploadLocalFiles.upload(this.recordInfo, {
            multiple: true,
            accessToken: true,
        });
        if (!attachments.length) {
            // No files selected or error during upload
            this.editable.focus();
            return;
        }
        if (this.config.onAttachmentChange) {
            attachments.forEach(this.config.onAttachmentChange);
        }
        // Render
        const fileCards = attachments.map(this.renderDownloadBox.bind(this));
        // Insert
        fileCards.forEach(this.dependencies.dom.insert);
        this.dependencies.history.addStep();
    }

    renderDownloadBox(attachment) {
        const url = this.services.uploadLocalFiles.getURL(attachment, {
            download: true,
            unique: true,
            accessToken: true,
        });
        const { name: filename, mimetype } = attachment;
        return renderStaticFileBox(filename, mimetype, url);
    }
}
