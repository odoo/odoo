import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BackgroundOption } from "@website/builder/plugins/background_option/background_option";
import { ParallaxOption } from "./parallax_option";
import { useBackgroundOption } from "@website/builder/plugins/background_option/background_hook";

export class WebsiteBackgroundOption extends BaseOptionComponent {
    static template = "website.WebsiteBackgroundOption";
    static components = {
        ...BackgroundOption.components,
        ParallaxOption,
    };
    static props = {
        ...BackgroundOption.props,
        withVideos: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...BackgroundOption.defaultProps,
        withVideos: false,
    };
    setup() {
        super.setup();
        const { showColorFilter } = useBackgroundOption(this.isActiveItem);
        this.showColorFilter = () => showColorFilter() || this.isActiveItem("toggle_bg_video_id");
        this.websiteBgOptionDomState = useDomState((el) => ({
            // Only search for .s_parallax_bg that are direct children
            applyTo: el.querySelector(":scope > .s_parallax_bg") ? ".s_parallax_bg" : "",
        }));
    }
}
