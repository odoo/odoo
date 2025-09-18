// @ts-check

/** @module @web/views/kanban/kanban_cover_image_dialog - Dialog for selecting, uploading, or removing a cover image on a kanban record */

import { Component, onWillStart, useState } from "@odoo/owl";
import { FileInput } from "@web/components/file_input/file_input";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog/dialog";

let nextDialogId = 1;

/**
 * Dialog for selecting or uploading a cover image on a kanban record.
 *
 * On open, fetches existing image attachments for the record. The user can
 * pick an existing attachment, upload a new image, or remove the current cover.
 */
export class KanbanCoverImageDialog extends Component {
    static template = "web.KanbanCoverImageDialog";
    static components = { Dialog, FileInput };
    static props = ["*"];
    setup() {
        this.id = `o_cover_image_upload_${nextDialogId++}`;
        this.orm = useService("orm");
        this.http = useService("http");
        const { record, fieldName } = this.props;
        const attachment = record.data[fieldName];
        this.state = useState({
            selectFile: false,
            selectedAttachmentId: attachment?.id || false,
        });
        onWillStart(async () => {
            this.attachments = await this.orm.searchRead(
                "ir.attachment",
                [
                    ["res_model", "=", record.resModel],
                    ["res_id", "=", record.resId],
                    ["mimetype", "ilike", "image"],
                ],
                ["id"],
            );
            this.state.selectFile = this.props.autoOpen && !!this.attachments.length;
        });
    }

    /** @returns {boolean} Whether the record currently has a cover image set. */
    get hasCoverImage() {
        return Boolean(this.props.record.data[this.props.fieldName]);
    }

    /**
     * Handle a completed file upload.
     * @param {Object[]} _ - Array with one uploaded attachment object.
     */
    onUpload([attachment]) {
        if (!attachment) {
            return;
        }
        this.state.selectFile = false;
        this.selectAttachment(attachment, true);
    }

    /**
     * Toggle selection of an attachment. If already selected, deselect it.
     * @param {Object} attachment - Attachment record with `id`.
     * @param {boolean} setSelected - If true, immediately persist the choice.
     */
    selectAttachment(attachment, setSelected) {
        if (this.state.selectedAttachmentId !== attachment.id) {
            this.state.selectedAttachmentId = attachment.id;
        } else {
            this.state.selectedAttachmentId = null;
        }
        if (setSelected) {
            this.setCover();
        }
    }

    /** Clear the cover image and persist the change. */
    removeCover() {
        this.state.selectedAttachmentId = null;
        this.setCover();
    }

    /** Persist the selected (or cleared) cover image to the record. */
    async setCover() {
        const value = this.state.selectedAttachmentId
            ? { id: this.state.selectedAttachmentId }
            : false;
        await this.props.record.update(
            { [this.props.fieldName]: value },
            { save: true },
        );
        this.props.close();
    }

    /** Show the file input widget. */
    uploadImage() {
        this.state.selectFile = true;
    }
}
