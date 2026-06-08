import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { props, t } from "@odoo/owl";
import { BackgroundImageOption } from "./background_image_option";
import { BackgroundPositionOption } from "./background_position_option";
import { BackgroundShapeOption } from "./background_shape_option";
import { useBackgroundOption } from "./background_hook";
import { ImageFilterOption } from "@html_builder/plugins/image/image_filter_option";
import { ImageFormatOption } from "@html_builder/plugins/image/image_format_option";

export const backgroundOptionProps = {
    withColors: t.boolean(),
    withImages: t.boolean(),
    withColorCombinations: t.boolean(),
    withShapes: t.boolean().optional(false),
};

export class BackgroundOption extends BaseOptionComponent {
    static template = "html_builder.BackgroundOption";
    static propShape = backgroundOptionProps;
    static components = {
        BackgroundImageOption,
        BackgroundPositionOption,
        BackgroundShapeOption,
        ImageFilterOption,
        ImageFormatOption,
    };
    props = props(this.constructor.propShape);

    setup() {
        super.setup();
        const { showColorFilter } = useBackgroundOption(this.isActiveItem);
        this.showColorFilter = showColorFilter;
    }
    computeMaxDisplayWidth() {
        return 1920;
    }
}
