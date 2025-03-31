import { BaseOptionComponent } from "@html_builder/core/utils";
import { ImageShapeOption } from "./image_shape_option";

export class ImageToolOption extends BaseOptionComponent {
    static template = "html_builder.ImageToolOption";
    static components = {
        ImageShapeOption,
    };
    static props = {};
}
