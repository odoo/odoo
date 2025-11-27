import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { ImageShapeOption } from "@html_builder/plugins/image/image_shape_option";
import { ImageFilterOption } from "@html_builder/plugins/image/image_filter_option";
import { ImageFormatOption } from "@html_builder/plugins/image/image_format_option";
import { ImageTransformOption } from "./image_transform_option";
import { MediaSizeOption } from "./media_size_option";

export class ImageToolOption extends BaseOptionComponent {
    static template = "html_builder.ImageToolOption";
    static components = {
        ImageShapeOption,
        ImageFilterOption,
        ImageFormatOption,
        ImageTransformOption,
        MediaSizeOption,
    };
    static selector = "img";
    static exclude = "[data-oe-type='image'] > img";
    static name = "imageToolOption";
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isImageAnimated: editingElement.classList.contains("o_animate"),
            isGridMode: editingElement.closest(".o_grid_mode, .o_grid"),
            isSocialMediaImg: editingElement.classList.contains("social_media_img"),
        }));
    }
}
