import { _t } from "@web/core/l10n/translation";
import { Component, useRef } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";

export class UploadButton extends Component {
    static template = "product.UploadButton";
    static props = {
        formData: { type: Object, optional: true},
        // See https://www.iana.org/assignments/media-types/media-types.xhtml
        allowedMIMETypes: { type: String, optional: true},
        load: Function,
        uploadRoute: String,
    }
    static defaultProps = {
        formData: {},
    }

    setup() {
        this.uploadFileInputRef = useRef("uploadFileInput");
        this.fileUploadService = useService("file_upload");
        this.notification = useService('notification');
        useBus(
            this.fileUploadService.bus,
            "FILE_UPLOAD_LOADED",
            async () => {
                await this.props.load();
            },
        );
    }

    async onFileInputChange(ev) {
        const files = [...ev.target.files].filter(file => this.validFileType(file));
        if (!files.length) {
            return;
        }
        await this.fileUploadService.upload(
            this.props.uploadRoute,
            files,
            {
                buildFormData: (formData) => this.buildFormData(formData)
            },
        );
        // Reset the file input's value so that the same file may be uploaded twice.
        ev.target.value = "";
    }

    /**
     * The `allowedMIMETypes` prop can restrict the file types users are guided to select. However,
     * the `accept` attribute doesn't enforce strict validation; it only suggests file types for
     * browsers.
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

    buildFormData(formData) {
        for (const [key, value] of Object.entries(this.props.formData)) {
            formData.append(key, value);
        }
    }

}
