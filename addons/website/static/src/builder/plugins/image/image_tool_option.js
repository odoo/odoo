import { BaseOptionComponent } from "@html_builder/core/utils";
import { ImageShapeOption } from "./image_shape_option";
import { ImageFilterOption } from "./image_filter_option";
import { ImageFormatOption } from "./image_format_option";

export class ImageToolOption extends BaseOptionComponent {
    static template = "website.ImageToolOption";
    static components = {
        ImageShapeOption,
        ImageFilterOption,
        ImageFormatOption,
    };
    static props = {};
}
