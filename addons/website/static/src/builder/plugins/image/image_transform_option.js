import { BaseOptionComponent } from "@html_builder/core/utils";
import { useTransformOperations } from "@html_editor/main/media/image_transform_button";
import { registry } from "@web/core/registry";

export class ImageTransformOption extends BaseOptionComponent {
    static template = "website.ImageTransformOption";

    setup() {
        super.setup();
        this.transformOperations = useTransformOperations({
            document: this.env.editor.document,
            closeImageTransformation: this.closeImageTransformation.bind(this),
        });
    }

    closeImageTransformation() {
        if (this.transformOperations.isImageTransformationOpen()) {
            registry.category("main_components").remove("ImageTransformation");
        }
    }
}
