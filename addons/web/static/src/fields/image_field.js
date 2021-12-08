/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { _lt } from "@web/core/l10n/translation";
import { FileUploader } from "./file_handler";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
const { useState } = owl.hooks;

export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
};
const placeholder = "/web/static/img/placeholder.png";

function isBinarySize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

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
        FileUploader,
    },

    displayName: _lt("Image"),
    supportedTypes: ["binary"],
});

registry.category("fields").add("image", ImageField);
