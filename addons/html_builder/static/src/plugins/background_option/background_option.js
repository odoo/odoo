import { BaseOptionComponent } from "@html_builder/core/utils";
import { BackgroundImageOption } from "./background_image_option";
import { BackgroundPositionOption } from "./background_position_option";
import { BackgroundShapeOption } from "./background_shape_option";
import { useBackgroundOption } from "./background_hook";
import { ImageFilterOption } from "@html_builder/plugins/image/image_filter_option";
import { ImageFormatOption } from "@html_builder/plugins/image/image_format_option";

export class BackgroundOption extends BaseOptionComponent {
    static template = "html_builder.BackgroundOption";
    static components = {
        BackgroundImageOption,
        BackgroundPositionOption,
        BackgroundShapeOption,
        ImageFilterOption,
        ImageFormatOption,
    };
    static props = {
        withColors: { type: Boolean },
        withImages: { type: Boolean },
        withColorCombinations: { type: Boolean },
        withShapes: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withShapes: false,
    };

    setup() {
        super.setup();
        const { showColorFilter } = useBackgroundOption(this.isActiveItem);
        this.showColorFilter = showColorFilter;
    }
    computeMaxDisplayWidth() {
        return 1920;
    }
}
