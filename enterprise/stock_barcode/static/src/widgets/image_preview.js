/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ImageField } from "@web/views/fields/image/image_field";
import { Component } from "@odoo/owl";

export class FullScreenImage extends Component {
    static template = "stock_barcode.FullScreenImage";
    static props = {
        src: {type: String},
        close: Function,
    };
}

export class ImagePreviewField extends ImageField {
    static template = "stock_barcode.ImagePreviewField";

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    openImageFullScreen() {
        this.dialog.add(FullScreenImage, {
            src: this.getUrl(this.props.name),
        });
    }
}

export const imageClickEnlarge = {
    component: ImagePreviewField,
};

registry.category("fields").add("image_preview", imageClickEnlarge);
