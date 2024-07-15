/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";

export class UploadButton extends Component {
    static template = "product.UploadButton";
    static props = {
        formData: { type: Object, optional: true},
        load: Function,
        uploadRoute: String,
    }
    static defaultProps = {
        formData: {},
    }

    setup() {
        this.uploadFileInputRef = useRef("uploadFileInput");
        this.fileUploadService = useService("file_upload");
        useBus(
            this.fileUploadService.bus,
            "FILE_UPLOAD_LOADED",
            async () => {
                await this.props.load();
            },
        );
    }

    async onFileInputChange(ev) {
        if (!ev.target.files.length) {
            return;
        }
        await this.fileUploadService.upload(
            this.props.uploadRoute,
            ev.target.files,
            {
                buildFormData: (formData) => this.buildFormData(formData)
            },
        );
        // Reset the file input's value so that the same file may be uploaded twice.
        ev.target.value = "";
    }

    buildFormData(formData) {
        for (const [key, value] of Object.entries(this.props.formData)) {
            formData.append(key, value);
        }
    }

}
