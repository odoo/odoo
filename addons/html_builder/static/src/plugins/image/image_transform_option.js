import { BaseOptionComponent } from "@html_builder/core/utils";
import { useImageTransform } from "@html_editor/main/media/image_transform_button";
import { onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ImageTransformOption extends BaseOptionComponent {
    static template = "website.ImageTransformOption";

    setup() {
        super.setup();
        this.transform = useImageTransform({
            document: document,
            closeImageTransformation: this.closeImageTransformation.bind(this),
            buttonSelector:
                '[data-action-id="transformImage"], [data-action-id="transformImage"] *',
        });
        onWillDestroy(() => {
            this.closeImageTransformation();
        });
    }

    closeImageTransformation() {
        if (this.transform.isImageTransformationOpen()) {
            registry.category("main_components").remove("ImageTransformation");
        }
    }
}
