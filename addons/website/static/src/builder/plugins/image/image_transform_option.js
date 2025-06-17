import { BaseOptionComponent } from "@html_builder/core/utils";
import { useTransformOperations } from "@html_editor/main/media/image_transform_button";
import { registry } from "@web/core/registry";

export class ImageTransformOption extends BaseOptionComponent {
    static template = "website.ImageTransformOption";

    setup() {
        super.setup();
        useTransformOperations({
            document: this.env.editor.document,
            isImageTransformationOpen: this.isImageTransformationOpen,
            closeImageTransformation: this.closeImageTransformation.bind(this),
        }); // ?
    }

    isImageTransformationOpen() {
        return registry.category("main_components").contains("ImageTransformation");
    }

    closeImageTransformation() {
        if (this.isImageTransformationOpen()) {
            registry.category("main_components").remove("ImageTransformation");
        }
    }
}
