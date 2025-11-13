import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SignatureViewer } from "@web/core/signature/signature_viewer";
import { isBinarySize } from "@web/core/utils/binary";
import { imageUrl } from "@web/core/utils/urls";
import { fileTypeMagicWordMap } from "@web/views/fields/image/image_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class SignatureField extends Component {
    static template = "web.SignatureField";
    static components = { SignatureViewer };
    static props = {
        ...standardFieldProps,
        defaultFont: { type: String },
        fullName: { type: String, optional: true },
        height: { type: Number, optional: true },
        previewImage: { type: String, optional: true },
        width: { type: Number, optional: true },
        type: { validate: (t) => ["initial", "signature"].includes(t), optional: true },
    };
    static defaultProps = {
        type: "signature",
    };

    get defaultName() {
        const { fullName, record } = this.props;
        let defaultName = "";
        if (fullName) {
            const fullNameData = record.data[fullName];
            if (record.fields[fullName].type === "many2one") {
                // If m2o is empty, it will have falsy value in recordData
                defaultName = fullNameData && fullNameData.display_name;
            } else {
                defaultName = fullNameData;
            }
        }
        return defaultName || "";
    }

    get rawCacheKey() {
        return this.props.record.data.write_date;
    }

    get url() {
        if (!this.value) {
            return "";
        }
        const { name, previewImage, record } = this.props;
        if (isBinarySize(this.value)) {
            return imageUrl(record.resModel, record.resId, previewImage || name, {
                unique: this.rawCacheKey,
            });
        } else {
            // Use magic-word technique for detecting image type
            const magic = fileTypeMagicWordMap[this.value[0]] || "png";
            return `data:image/${magic};base64,${this.value}`;
        }
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    /**
     * Upload the signature image if valid and close the dialog.
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
