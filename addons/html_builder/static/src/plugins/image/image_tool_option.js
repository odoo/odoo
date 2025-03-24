import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { ImageShapeOption } from "./image_shape_option";

export class ImageToolOption extends BaseOptionComponent {
    static template = "html_builder.ImageToolOption";
    static components = {
        ImageShapeOption,
    };
    static props = {};
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isCustomFilter: editingElement.dataset.glFilter === "custom",
        }));
    }
}
