// @ts-check

/** @module @web/fields/media/signature/signature_field - Signature pad field for capturing and storing handwritten signatures */

import { Component, useState } from "@odoo/owl";
import { SignatureDialog } from "@web/components/signature/signature_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { isBinarySize } from "@web/core/utils/format/binary";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { fileTypeMagicWordMap } from "@web/fields/media/image/image_field";
import { standardFieldProps } from "@web/fields/standard_field_props";

const placeholder = "/web/static/img/placeholder.png";

export class SignatureField extends Component {
    static template = "web.SignatureField";
    static props = {
        ...standardFieldProps,
        defaultFont: { type: String },
        fullName: { type: String, optional: true },
        height: { type: Number, optional: true },
        previewImage: { type: String, optional: true },
        width: { type: Number, optional: true },
        type: {
            validate: (t) => ["initial", "signature"].includes(t),
            optional: true,
        },
    };
    static defaultProps = {
        type: "signature",
    };

    setup() {
        this.displaySignatureRatio = 3;

        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            isValid: true,
        });
    }

    /** @returns {string} Cache-busting key based on record write date */
    get rawCacheKey() {
        return this.props.record.data.write_date;
    }

    /** @returns {string} Image URL for the signature or a placeholder */
    get getUrl() {
        const { name, previewImage, record } = this.props;
        if (this.state.isValid && this.value) {
            if (isBinarySize(this.value)) {
                return imageUrl(record.resModel, record.resId, previewImage || name, {
                    unique: this.rawCacheKey,
                });
            } else {
                // Use magic-word technique for detecting image type
                const magic = fileTypeMagicWordMap[this.value[0]] || "png";
                return `data:image/${magic};base64,${this.props.record.data[this.props.name]}`;
            }
        }
        return placeholder;
    }

    /** @returns {string} Inline CSS style string for signature dimensions */
    get sizeStyle() {
        let { width, height } = this.props;

        if (!this.value) {
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

    /** @returns {string|false} Raw binary data of the signature field */
    get value() {
        return this.props.record.data[this.props.name];
    }

    /** Opens the signature dialog when the field is editable */
    onClickSignature() {
        if (!this.props.readonly) {
            const nameAndSignatureProps = {
                displaySignatureRatio: 3,
                signatureType: this.props.type,
                noInputName: true,
            };
            const { fullName, record } = this.props;
            let defaultName = "";
            if (fullName) {
                let signName;
                const fullNameData = record.data[fullName];
                if (record.fields[fullName].type === "many2one") {
                    // If m2o is empty, it will have falsy value in recordData
                    signName = fullNameData?.display_name;
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

    /** Marks the image as invalid and shows an error notification */
    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(_t("Could not display the selected image"), {
            type: "danger",
        });
    }

    /**
     * Upload the signature image if valid and close the dialog.
     *
     * @private
     */
    uploadSignature({ signatureImage }) {
        return this.props.record.update({
            [this.props.name]: signatureImage.split(",")[1] || false,
        });
    }
}

export const signatureField = {
    component: SignatureField,
    fieldDependencies: [{ name: "write_date", type: "datetime" }],
    supportedTypes: ["binary"],
    supportedOptions: [
        {
            label: _t("Prefill with"),
            name: "full_name",
            type: "field",
            availableTypes: ["char", "many2one"],
            help: _t("The selected field will be used to pre-fill the signature"),
        },
        {
            label: _t("Default font"),
            name: "default_font",
            type: "string",
        },
        {
            label: _t("Size"),
            name: "size",
            type: "selection",
            choices: [
                { label: _t("Small"), value: "[0,90]" },
                { label: _t("Medium"), value: "[0,180]" },
                { label: _t("Large"), value: "[0,270]" },
            ],
        },
        {
            label: _t("Preview image field"),
            name: "preview_image",
            type: "field",
            availableTypes: ["binary"],
        },
    ],
    extractProps: ({ attrs, options }) => ({
        defaultFont: options.default_font || "",
        fullName: options.full_name,
        height: options.size ? options.size[1] || undefined : attrs.height,
        previewImage: options.preview_image,
        type: options.type,
        width: options.size ? options.size[0] || undefined : attrs.width,
    }),
};

registry.category("fields").add("signature", signatureField);
