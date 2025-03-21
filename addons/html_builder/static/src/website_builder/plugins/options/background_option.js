import { useDomState } from "@html_builder/core/utils";
import { BackgroundImageOption } from "@html_builder/plugins/background_option/background_image_option";
import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { BackgroundPositionOption } from "@html_builder/plugins/background_option/background_position_option";
import { BackgroundShapeOption } from "@html_builder/plugins/background_option/background_shape_option";
import { ParallaxOption } from "../parallax_option";

export class WebsiteBackgroundOption extends BackgroundOption {
    static template = "website.WebsiteBackgroundOption";
    static components = {
        BackgroundImageOption,
        BackgroundPositionOption,
        BackgroundShapeOption,
        ParallaxOption,
    };
    static props = {
        ...super.props,
        withVideos: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withVideos: false,
    };
    setup() {
        super.setup();
        this.websiteBgOptionDomState = useDomState((el) => ({
            applyTo: el.querySelector(".s_parallax_bg") ? ".s_parallax_bg" : "",
        }));
    }
    showColorFilter() {
        return super.showColorFilter() || this.isActiveItem("toggle_bg_video_id");
    }
}
