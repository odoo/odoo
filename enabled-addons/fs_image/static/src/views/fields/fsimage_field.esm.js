/**
 * Copyright 2023 ACSONE SA/NV
 */
import {
    ImageField,
    fileTypeMagicWordMap,
    imageField,
} from "@web/views/fields/image/image_field";
import {AltTextDialog} from "../dialogs/alttext_dialog.esm";
import {_t} from "@web/core/l10n/translation";
import {download, downloadFile} from "@web/core/network/download";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {url as utilUrl} from "@web/core/utils/urls";

const placeholder = "/web/static/img/placeholder.png";

export class FSImageField extends ImageField {
    setup() {
        // Call super.setup() to initialize the state
        super.setup();
        this.dialogService = useService("dialog");
    }

    getUrl(previewFieldName) {
        if (
            this.state.isValid &&
            this.props.record.data[this.props.name] &&
            typeof this.props.record.data[this.props.name] === "object"
        ) {
            // Check if value is a dict
            if (this.props.record.data[this.props.name].content) {
                // We use the binary content of the value
                // Use magic-word technique for detecting image type
                const magic =
                    fileTypeMagicWordMap[
                        this.props.record.data[this.props.name].content[0]
                    ] || "png";
                return `data:image/${magic};base64,${
                    this.props.record.data[this.props.name].content
                }`;
            }
            const model = this.props.record.resModel;
            const id = this.props.record.resId;
            let base_url = this.props.record.data[this.props.name].url;
            if (id !== undefined && id !== null && id !== false) {
                const field = previewFieldName;
                const filename = this.props.record.data[this.props.name].filename;
                base_url = `/web/image/${model}/${id}/${field}/${filename}`;
            }
            return utilUrl(base_url, {unique: this.rawCacheKey});
        }
        return placeholder;
    }

    async onFileUploaded(info) {
        this.props.record.update({
            [this.props.name]: {
                filename: info.name,
                content: info.data,
            },
        });
    }
    onAltTextEdit() {
        const self = this;
        const altText = this.props.record.data[this.props.name].alt_text || "";
        const dialogProps = {
            title: _t("Alt Text"),
            altText: altText,
            confirm: (value) => {
                self.props.record.update({
                    [self.props.name]: {
                        ...this.props.record.data[this.props.name],
                        alt_text: value,
                    },
                });
            },
        };
        this.dialogService.add(AltTextDialog, dialogProps);
    }
    async onFileDownload() {
        if (this.props.value.content) {
            const magic = fileTypeMagicWordMap[this.props.value.content[0]] || "png";
            await downloadFile(
                `data:image/${magic};base64,${this.props.value.content}`,
                this.state.filename,
                `image/${magic}`
            );
        } else {
            await download({
                data: {
                    model: this.props.record.resModel,
                    id: this.props.record.resId,
                    field: this.props.name,
                    filename: this.state.filename || "download",
                    download: true,
                },
                url: "/web/image",
            });
        }
    }
}

FSImageField.template = "fs_image.FSImageField";

export const fSImageField = {
    ...imageField,
    component: FSImageField,
};

registry.category("fields").add("fs_image", fSImageField);
