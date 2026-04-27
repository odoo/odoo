/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, useRef } from "@odoo/owl";
import { formatDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { download } from "@web/core/network/download";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class DocumentsManageVersions extends Component {
    static components = {
        Dialog,
    };
    static props = {
        documentId: Number,
        close: Function,
    };
    static template = "documents.ManageVersions";

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.documentService = useService("document.document");
        this.fileUploadService = useService("file_upload");
        this.fileInputRef = useRef("uploadFileInput");
        this.formatDate = (d) => formatDateTime(deserializeDateTime(d), { format: "HH:mm DDD" });

        this.state = useState({ documentName: "", accessToken: "", versions: [] });

        onWillStart(async () => await this.load());
        useBus(this.fileUploadService.bus, "FILE_UPLOAD_LOADED", async () => await this.load());
    }

    async load() {
        const attachmentFields = {
            name: 1,
            create_date: 1,
            mimetype: 1,
            create_uid: { fields: { name: 1 } },
        };
        const documentData = await this.orm.call("documents.document", "web_read", [
            this.props.documentId,
            {
                name: 1,
                access_token: 1,
                user_permission: 1,
                attachment_id: { fields: attachmentFields },
                previous_attachment_ids: { fields: attachmentFields },
            },
        ]);

        Object.assign(this.state, {
            documentName: documentData[0].name,
            userPermission: documentData[0].user_permission,
            accessToken: documentData[0].access_token,
            versions: [documentData[0].attachment_id, ...documentData[0].previous_attachment_ids],
        });
    }

    get panelTitle() {
        return _t('Manage Versions of "%s"', this.state.documentName);
    }

    onUploadNewVersion() {
        this.fileInputRef.el.click();
    }

    async onReplace(ev) {
        if (!ev.target.files.length) {
            return;
        }
        await this.documentService.uploadDocument(ev.target.files, this.state.accessToken, {
            document_id: this.props.documentId,
        });
        ev.target.value = "";
    }

    async onDownload(attachmentId) {
        await download({
            data: {},
            url: `/web/content/${attachmentId}?download=true`,
        });
    }

    async onDelete(attachmentId) {
        return this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this attachment?"),
            confirmLabel: "Delete",
            confirm: async () => {
                await this.orm.call("documents.document", "action_delete_from_history", [
                    this.props.documentId,
                    attachmentId,
                ]);
                await this.load();
                this.documentService.reload();
            },
            cancel: () => {},
        });
    }
}
