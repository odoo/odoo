/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { sprintf } from "@web/core/utils/strings";
import { formatFloat } from "./formatters";

const { Component } = owl;
const { useRef, useState } = owl.hooks;

export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
};

const DEFAULT_MAX_FILE_SIZE = 128 * 1024 * 1024;

/**
 * Gets dataURL (base64 data) from the given file or blob.
 * Technically wraps FileReader.readAsDataURL in Promise.
 *
 * @param {Blob | File} file
 * @returns {Promise} resolved with the dataURL, or rejected if the file is
 *  empty or if an error occurs.
 */
function getDataURLFromFile(file) {
    if (!file) {
        return Promise.reject();
    }
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.addEventListener("load", () => resolve(reader.result));
        reader.addEventListener("abort", reject);
        reader.addEventListener("error", reject);
        reader.readAsDataURL(file);
    });
}

export class FileUploader extends Component {
    setup() {
        this.notification = useService("notification");
        this.id = `o_fileupload_${++FileUploader.nextId}`;
        this.state = useState({
            isUploading: false,
        });
        this.fileInputRef = useRef("fileInput");
    }

    get maxUploadSize() {
        return session.max_file_upload_size || DEFAULT_MAX_FILE_SIZE;
    }
    /**
     * @param {Event} ev
     */
    async onFileChange(ev) {
        if (ev.target.files.length) {
            const file = ev.target.files[0];
            if (file.size > this.maxUploadSize) {
                this.notification.add(
                    sprintf(
                        this.env._t("The selected file exceed the maximum file size of %s."),
                        formatFloat(this.maxUploadSize, { humanReadable: true })
                    ),
                    {
                        title: this.env._t("File upload"),
                        type: "danger",
                    }
                );
            }
            this.state.isUploading = true;
            const data = await getDataURLFromFile(file);
            if (!file.size) {
                console.warn(`Error while uploading file : ${file.name}`);
                this.notification.add(
                    this.env._t("There was a problem while uploading your file."),
                    { type: "danger" }
                );
            }
            this.props.onUploaded({
                name: file.name,
                size: file.size,
                type: file.type,
                data: data.split(",")[1],
            });
            this.state.isUploading = false;
        }
    }
    onSelectFileButtonClick() {
        this.fileInputRef.el.click();
    }
    onClearFileButtonClick() {
        this.fileInputRef.el.value = "";
        this.props.onRemove();
    }
}
FileUploader.props = {
    onUploaded: Function,
    onRemove: Function,
    file: Object | null,
    fileUploadClass: { type: String, optional: true },
    fileUploadStyle: { type: String, optional: true },
    fileUploadAction: { type: String, optional: true },
    multiUpload: { type: Boolean, optional: true },
    acceptedFileExtensions: { type: String, optional: true },
    required: { type: Boolean, optional: true },
    type: { type: String, optional: true },
};
FileUploader.template = "web.FileUploader";

FileUploader.nextId = 0;

export class FileDownloader extends Component {
    onDownloadButtonClick() {
        this.props.onDownload();
    }
}
FileDownloader.props = {
    file: Object | null,
    fileDownloadAction: { type: String, optional: true },
    onDownload: Function,
};
FileDownloader.template = "web.FileDownloader";
