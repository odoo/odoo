import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ImageField, imageField } from "@web/views/fields/image/image_field";
import { save } from "@web/core/utils/image_library"
import { CustomMediaDialog } from "@html_editor/fields/x2many_field/custom_media_dialog";

export class ImageFieldWithMediaDialog extends ImageField {
    static template = "html_editor.ImageFieldWithMediaDialog";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
    }

    onFileEdit(ev) {
        this.dialog.add(CustomMediaDialog, {
            visibleTabs: ["IMAGES"],
            activeTab: "IMAGES",
            save: (el) => {}, // Simple rebound to fake its execution
            imageSave: this.onImageSave.bind(this),
        });
    }

    async onImageSave(attachment) {
        await save(this.env, {
            attachments: attachment,
            targetRecord: this.props.record,
            targetFieldName: this.props.name,
            changeRecordName: false,
        })
    }
}

export const imageFieldWithMediaDialog = {
    ...imageField,
    component: ImageFieldWithMediaDialog,
};

registry.category("fields").add("image_with_media_dialog", imageFieldWithMediaDialog);
