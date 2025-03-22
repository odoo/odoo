/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { checkFileSize } from "@web/core/utils/files";
import { getDataURLFromFile } from "@web/core/utils/urls";

import { Component, useRef, useState } from "@odoo/owl";

export class FileUploader extends Component {
    setup() {
        this.notification = useService("notification");
        this.fileInputRef = useRef("fileInput");
        this.state = useState({
            isUploading: false,
        });
    }

    /**
     * @param {Event} ev
     */
    async onFileChange(ev) {
        if (!ev.target.files.length) {
            return;
        }
        const { target } = ev;
        for (const file of ev.target.files) {
            if (!checkFileSize(file.size, this.notification)) {
                return null;
            }
            this.state.isUploading = true;
            const data = await getDataURLFromFile(file);
            if (!file.size) {
                console.warn(`Error while uploading file : ${file.name}`);
                this.notification.add(
                    this.env._t("There was a problem while uploading your file."),
                    {
                        type: "danger",
                    }
                );
            }
            try {
                await this.props.onUploaded({
                    name: file.name,
                    size: file.size,
                    type: file.type,
                    data: data.split(",")[1],
                    objectUrl: file.type === "application/pdf" ? URL.createObjectURL(file) : null,
                });
            } finally {
                this.state.isUploading = false;
            }
        }
        target.value = null;
        if (this.props.multiUpload && this.props.onUploadComplete) {
            this.props.onUploadComplete({});
        }
    }

    onSelectFileButtonClick() {
        this.fileInputRef.el.click();
    }
}

FileUploader.template = "web.FileUploader";
