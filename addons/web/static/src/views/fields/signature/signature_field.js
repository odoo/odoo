/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SignatureDialog } from "@web/core/signature/signature_dialog";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { isBinarySize } from "@web/core/utils/binary";
import { fileTypeMagicWordMap, imageCacheKey } from "@web/views/fields/image/image_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

const placeholder = "/web/static/img/placeholder.png";

export class SignatureField extends Component {
    setup() {
        this.displaySignatureRatio = 3;

        this.dialogService = useService("dialog");
        this.state = useState({
            isValid: true,
        });

        this.rawCacheKey = this.props.record.data.write_date;
        onWillUpdateProps((nextProps) => {
            const { record } = this.props;
            const { record: nextRecord } = nextProps;
            if (record.resId !== nextRecord.resId || nextRecord.mode === "readonly") {
                this.rawCacheKey = nextRecord.data.write_date;
            }
        });
    }

    get getUrl() {
        const { name, previewImage, record, value } = this.props;
        if (this.state.isValid && value) {
            if (isBinarySize(value)) {
                return url("/web/image", {
                    model: record.resModel,
                    id: record.resId,
                    field: previewImage || name,
                    unique: imageCacheKey(this.rawCacheKey),
                });
            } else {
                // Use magic-word technique for detecting image type
                const magic = fileTypeMagicWordMap[this.props.value[0]] || "png";
                return `data:image/${magic};base64,${this.props.value}`;
            }
        }
        return placeholder;
    }

    get sizeStyle() {
        let { width, height, value } = this.props;

        if (!value) {
            if (width && height) {
                width = Math.min(width, this.displaySignatureRatio * height);
                height = width / this.displaySignatureRatio;
            } else if (width) {
                height = width / this.displaySignatureRatio;
            } else if (height) {
                width = height * this.displaySignatureRatio;
            }
        }

        let style = "";
        if (width) {
            style += `width:${width}px; max-width:${width}px;`;
        }
        if (height) {
            style += `height:${height}px; max-height:${height}px;`;
        }
        return style;
    }

    onClickSignature() {
        if (!this.props.readonly) {
            const nameAndSignatureProps = {
                mode: "draw",
                displaySignatureRatio: 3,
                signatureType: "signature",
                noInputName: true,
            };
            const { fullName, record } = this.props;
            let defaultName = "";
            if (fullName) {
                let signName;
                const fullNameData = record.data[fullName];
                if (record.fields[fullName].type === "many2one") {
                    // If m2o is empty, it will have falsy value in recordData
                    signName = fullNameData && fullNameData[1];
                } else {
                    signName = fullNameData;
                }
                defaultName = signName === "" ? undefined : signName;
            }

            nameAndSignatureProps.defaultFont = this.props.defaultFont;

            const dialogProps = {
                defaultName,
                nameAndSignatureProps,
                uploadSignature: (signature) => this.uploadSignature(signature),
            };
            this.dialogService.add(SignatureDialog, dialogProps);
        }
    }

    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(this.env._t("Could not display the selected image"), {
            type: "danger",
        });
    }

    /**
     * Upload the signature image if valid and close the dialog.
     *
     * @private
     */
    uploadSignature({ signatureImage }) {
        return this.props.update(signatureImage[1] || false);
    }
}

SignatureField.template = "web.SignatureField";
SignatureField.props = {
    ...standardFieldProps,
    defaultFont: { type: String },
    fullName: { type: String, optional: true },
    height: { type: Number, optional: true },
    previewImage: { type: String, optional: true },
    width: { type: Number, optional: true },
};
SignatureField.extractProps = ({ attrs }) => {
    const { options, width, height } = attrs;
    return {
        defaultFont: attrs.options.default_font || "",
        fullName: attrs.options.full_name,
        height: options.size ? options.size[1] || undefined : height,
        previewImage: attrs.options.preview_image,
        width: options.size ? options.size[0] || undefined : width,
    };
};

registry.category("fields").add("signature", SignatureField);
