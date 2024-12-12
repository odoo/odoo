import {
    DocumentSelector,
    renderStaticFileCard,
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
            keywords: ["file"],
        },
        power_buttons: withSequence(5, { commandId: "uploadFile" }),
        media_dialog_tabs_providers: this.media_dialog_tab_provider.bind(this),
        selectors_for_feff_providers: () => ".o_file_card",
    };

    get recordInfo() {
        return this.config.getRecordInfo?.() || {};
    }

    isUploadCommandAvailable() {
        return !this.config.disableFile;
    }

    media_dialog_tab_provider() {
        if (this.config.disableFile) {
            return [];
        }
        return [
            {
                id: "DOCUMENTS",
                title: _t("Documents"),
                Component: this.componentForMediaDialog,
                sequence: 15,
            },
        ];
    }

    get componentForMediaDialog() {
        return DocumentSelector;
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
        // TODO: prepend host to URL
        const url = this.services.uploadLocalFiles.getURL(attachment, {
            download: true,
            unique: true,
            accessToken: true,
        });
        const { name: filename, mimetype } = attachment;
        return renderStaticFileCard(filename, mimetype, url);
    }
}
