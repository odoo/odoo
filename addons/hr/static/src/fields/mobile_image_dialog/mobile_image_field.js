import { ImageField, imageField, imageFieldProps } from "@web/views/fields/image/image_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { t, useProps } from "@odoo/owl";

export class MobileImageDialog extends ImageField {
    static template = "hr.MobileImageDialog";
    static components = { Dialog, FileUploader };
    static props = {
        ...imageFieldProps,
        title: t.string().optional(),
        close: t.function().optional(),
    };
    props = useProps(this.constructor.props);

    async onFileUploaded(info) {
        await super.onFileUploaded(info);
        this.props.close();
    }

    onFileRemove() {
        super.onFileRemove();
        this.props.close();
    }
}

export class MobileImageField extends ImageField {
    static template = "hr.MobileImageField";
    static props = {
        ...imageFieldProps,
        dialogTitle: t.string().optional(),
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.ui = useService("ui");
    }

    onImageClick() {
        this.dialog.add(MobileImageDialog, {
                title: this.props.dialogTitle ? _t(this.props.dialogTitle) : _t("Avatar"),
                record: this.props.record,
                name: this.props.name,
                previewImage: this.props.previewImage || "avatar_128",
            });
    }
}

export const mobileImageField = {
    ...imageField,
    component: MobileImageField,
    extractProps: (fieldInfo) => {
        const props = imageField.extractProps(fieldInfo);
        props.dialogTitle = fieldInfo.options.title;
        return props;
    },
};

registry.category("fields").add("mobile_image", mobileImageField);
