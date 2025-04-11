import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { checkFileSize } from "@web/core/utils/files";

import { Component, useRef, useState } from "@odoo/owl";

export class FileUploader extends Component {
    static template = "web.FileUploader";
    static props = {
        onClick: { type: Function, optional: true },
        onUploaded: Function,
        onUploadComplete: { type: Function, optional: true },
        multiUpload: { type: Boolean, optional: true },
        checkSize: { type: Boolean, optional: true },
        inputName: { type: String, optional: true },
        fileUploadClass: { type: String, optional: true },
        acceptedFileExtensions: { type: String, optional: true },
        slots: { type: Object, optional: true },
        showUploadingText: { type: Boolean, optional: true },
        // See https://www.iana.org/assignments/media-types/media-types.xhtml
        allowedMIMETypes: { type: String, optional: true },
    };
    static defaultProps = {
        checkSize: true,
        showUploadingText: true,
    };

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
        const files = [...ev.target.files].filter(file => this.validFileType(file));
        if (!files. length) {
            return;
        }
        const { target } = ev;
        for (const file of files) {
            if (this.props.checkSize && !checkFileSize(file.size, this.notification)) {
                return null;
            }
            this.state.isUploading = true;
            const data = await getDataURLFromFile(file);
            if (!file.size) {
                console.warn(`Error while uploading file : ${file.name}`);
                this.notification.add(_t("There was a problem while uploading your file."), {
                    type: "danger",
                });
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

    /**
     * The `allowedMIMETypes` props can restrict the file types users are guided to select.
     * However, the `acceptedFileExtensions` attribute doesn't enforce strict validation;
     * it only suggests file types for browsers.
     *
     * @param {File} file
     * @returns Whether the upload file's type is in the whitelist (`allowedMIMETypes`).
     */
     validFileType(file) {
        if (this.props.allowedMIMETypes && !this.props.allowedMIMETypes.includes(file.type)) {
            this.notification.add(
                _t(`Oops! '%(fileName)s' didn’t upload since its format isn’t allowed.`, {
                    fileName: file.name,
                }),
                {
                    type: "danger",
                }
            );
            return false;
        }
        return true;
    }

    async onSelectFileButtonClick(ev) {
        if (this.props.onClick) {
            const ok = await this.props.onClick(ev);
            if (ok !== undefined && !ok) {
                return;
            }
        }
        this.fileInputRef.el.click();
    }
}
