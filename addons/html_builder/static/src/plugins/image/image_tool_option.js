import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { ImageShapeOption } from "@html_builder/plugins/image/image_shape_option";
import { ImageFilterOption } from "@html_builder/plugins/image/image_filter_option";
import { ImageFormatOption } from "@html_builder/plugins/image/image_format_option";
import { ImageTransformOption } from "./image_transform_option";
import { MediaSizeOption } from "./media_size_option";
import { BorderConfigurator } from "../border_configurator_option";
import { ShadowOption } from "../shadow_option";

export class ImageToolOption extends BaseOptionComponent {
    static template = "html_builder.ImageToolOption";
    static components = {
        ImageShapeOption,
        ImageFilterOption,
        ImageFormatOption,
        ImageTransformOption,
        MediaSizeOption,
        BorderConfigurator,
        ShadowOption,
    };
    static selector = "img";
    static exclude = "[data-oe-type='image'] > img";
    static name = "imageToolOption";
    static dependencies = ["imageShapeOption"];
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const shape = editingElement.dataset.shape;
            return {
                hasImageShapeClass: !!this.dependencies.imageShapeOption.getImageShapeClass(shape),
                isImageAnimated: editingElement.classList.contains("o_animate"),
                isGridMode: editingElement.closest(".o_grid_mode, .o_grid"),
                isSocialMediaImg: editingElement.classList.contains("social_media_img"),
            };
        });
    }
}
