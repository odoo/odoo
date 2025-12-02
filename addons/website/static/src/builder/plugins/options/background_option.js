import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { ParallaxOption } from "./parallax_option";
import { useBackgroundOption } from "@html_builder/plugins/background_option/background_hook";
import { registry } from "@web/core/registry";

export class WebsiteBackgroundOption extends BaseOptionComponent {
    static id = "website_background_option";
    static template = "website.WebsiteBackgroundOption";
    static components = {
        ...BackgroundOption.components,
        ParallaxOption,
    };
    static props = {
        ...BackgroundOption.props,
        withColors: { type: Boolean, optional: true },
        withImages: { type: Boolean, optional: true },
        withColorCombinations: { type: Boolean, optional: true },
        withVideos: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...BackgroundOption.defaultProps,
        withColors: true,
        withImages: true,
        withColorCombinations: true,
        withVideos: false,
    };
    setup() {
        super.setup();
        const { showColorFilter } = useBackgroundOption(this.isActiveItem);
        this.showColorFilter = () => showColorFilter() || this.isActiveItem("toggle_bg_video_id");
        // ":scope > .s_parallax_bg" is kept for compatibility.
        const parallaxBgSelector =
            ":scope > .s_parallax_bg, :scope > .s_parallax_bg_wrap > .s_parallax_bg";
        this.websiteBgOptionDomState = useDomState((el) => ({
            // Only search for .s_parallax_bg that are direct children
            applyTo: el.querySelector(parallaxBgSelector) ? parallaxBgSelector : "",
        }));
    }
}

registry.category("builder-options").add(WebsiteBackgroundOption.id, WebsiteBackgroundOption);
