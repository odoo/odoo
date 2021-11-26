/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { session } from "@web/session";
import { _lt } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { formatFloat } from "./formatters";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
const { useRef, useState } = owl.hooks;

export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
};
const placeholder = "/web/static/img/placeholder.png";

const DEFAULT_MAX_FILE_SIZE = 128 * 1024 * 1024;

function isBinarySize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}
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

class ImageUploader extends Component {
    setup() {
        this.notification = useService("notification");
        this.id = `o_fileupload_${++ImageUploader.nextId}`;
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
            this.state.isUploading = false;
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
ImageUploader.template = "web.ImageUploader";
ImageUploader.props = {
    onUploaded: Function,
    onRemove: Function,
    fileUploadClass: { type: String, optional: true },
    fileUploadStyle: { type: String, optional: true },
    fileUploadAction: { type: String, optional: true },
    multiUpload: { type: Boolean, optional: true },
    acceptedFileExtensions: { type: String, optional: true },
};

ImageUploader.nextId = 0;

export class ImageField extends Component {
    setup() {
        this.notification = useService("notification");

        this.state = useState({
            isValid: true,
        });
    }
    get url() {
        if (this.state.isValid && this.props.value) {
            if (isBinarySize(this.props.value)) {
                const previewFieldName = this.props.options.preview_image || this.props.name;
                return url("/web/image", {
                    model: this.props.record.resModel,
                    id: this.props.record.resId,
                    field: previewFieldName,
                });
            } else {
                // Use magic-word technique for detecting image type
                const magic = fileTypeMagicWordMap[this.props.value[0]] || "png";
                return `data:image/${magic};base64,${this.props.value}`;
            }
        }
        return placeholder;
    }

    onFileRemove() {
        this.state.isValid = true;
        this.props.update(false);
    }
    onFileUploaded(info) {
        this.state.isValid = true;
        this.props.update(info.data);
    }
    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(this.env._t("Could not display the selected image"), {
            type: "danger",
        });
    }
}

Object.assign(ImageField, {
    template: "web.ImageField",
    props: {
        ...standardFieldProps,
    },
    components: {
        ImageUploader,
    },

    displayName: _lt("Image"),
    supportedTypes: ["binary"],
});

registry.category("fields").add("image", ImageField);
