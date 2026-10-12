import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { ImageShapeOption } from "@html_builder/plugins/image/image_shape_option";
import { ImageFilterOption } from "@html_builder/plugins/image/image_filter_option";
import { ImageFormatOption } from "@html_builder/plugins/image/image_format_option";
import { ImageTransformOption } from "./image_transform_option";
import { MediaSizeOption } from "./media_size_option";
import { dynamicSVGSelector } from "../utils";
import { registry } from "@web/core/registry";
import { getMimetypeBeforeShape } from "@html_builder/utils/image";
import { isImageSupportedForProcessing } from "@html_editor/main/media/image_post_process_plugin";

export class ImageToolOption extends BaseOptionComponent {
    static id = "image_tool_option";
    static template = "html_builder.ImageToolOption";
    static components = {
        ImageShapeOption,
        ImageFilterOption,
        ImageFormatOption,
        ImageTransformOption,
        MediaSizeOption,
    };
    setup() {
        super.setup();
        this.state = useDomState(async (editingElement) => {
            const mimetype = await getMimetypeBeforeShape(editingElement);
            const showCropTool = await isImageSupportedForProcessing(editingElement, mimetype);
            return {
                isImageAnimated: editingElement.classList.contains("o_animate"),
                isGridMode: editingElement.closest(".o_grid_mode, .o_grid"),
                isSocialMediaImg: editingElement.classList.contains("social_media_img"),
                isDynamicSVG: editingElement.matches(dynamicSVGSelector),
                isImageBinaryField: editingElement.parentElement.matches("[data-oe-type=image]"),
                showCropTool,
            };
        });
    }
}

registry.category("builder-options").add(ImageToolOption.id, ImageToolOption);
