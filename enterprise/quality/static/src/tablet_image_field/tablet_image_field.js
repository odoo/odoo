/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ImageField, imageField } from '@web/views/fields/image/image_field';
import { Component } from "@odoo/owl";

class ImagePreviewDialog extends Component {
    static components = { Dialog };
    static template = "quality.ImagePreviewDialog";
    static props = {
        src: String,
        close: Function,
    };
}

export class TabletImageField extends ImageField {
    static template = "quality.TabletImageField";

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

export const tabletImageField = {
    ...imageField,
    component: TabletImageField,
};

registry.category("fields").add("tablet_image", tabletImageField);
