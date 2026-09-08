import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { checkFileSize } from "@web/core/utils/files";
import { isBrowserChrome } from "@web/core/browser/feature_detection";

import { Component, proxy, signal, t, useProps } from "@odoo/owl";

export class FileUploader extends Component {
    static template = "web.FileUploader";
    props = useProps({
        onClick: t.function().optional(),
        onUploaded: t.function(),
        onUploadComplete: t.function().optional(),
        multiUpload: t.boolean().optional(),
        checkSize: t.boolean().optional(true),
        inputName: t.string().optional(),
        fileUploadClass: t.string().optional(),
        acceptedFileExtensions: t.string().optional(),
        showUploadingText: t.boolean().optional(true),
        // See https://www.iana.org/assignments/media-types/media-t.xhtml
        allowedMIMETypes: t.string().optional(),
    });

    fileInputRef = signal.ref();

    setup() {
        this.notification = useService("notification");
        this.state = proxy({
            isUploading: false,
        });
    }

    /**
     * @param {Event} ev
     */
    async onFileChange(ev) {
        await this.uploadFiles(Array.from(ev.target.files));
        ev.target.value = null;
    }

    /**
     * @param {File[]} files
     */
    async uploadFiles(files) {
        const validFiles = files.filter((file) => this.validFileType(file));
        if (!files.length) {
            return;
        }
        for (const file of validFiles) {
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
        if (isBrowserChrome()) {
            const pickerOpts = { multiple: this.props.multiUpload };
            const fileHandles = await window.showOpenFilePicker(pickerOpts);
            this.uploadFiles(await Promise.all(fileHandles.map((handle) => handle.getFile())));
        } else {
            this.fileInputRef()?.click();
        }
    }
}
