/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ImageField, imageField } from '@web/views/fields/image/image_field';
import { Component } from "@odoo/owl";

class ImagePreviewDialog extends Component {}
ImagePreviewDialog.components = { Dialog };
ImagePreviewDialog.template = "quality.ImagePreviewDialog";

export class TabletImageField extends ImageField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    openModal() {
        this.dialog.add(ImagePreviewDialog, {
            src: this.getUrl(this.props.name),
        });
    }
}

TabletImageField.template = "quality.TabletImageField";

export const tabletImageField = {
    ...imageField,
    component: TabletImageField,
};

registry.category("fields").add("tablet_image", tabletImageField);
