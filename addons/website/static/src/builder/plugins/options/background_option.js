import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import {
    BackgroundOption,
    backgroundOptionProps,
} from "@html_builder/plugins/background_option/background_option";
import { ParallaxOption } from "./parallax_option";
import { BgBlurOption } from "./bg_blur_option_plugin";
import { useBackgroundOption } from "@html_builder/plugins/background_option/background_hook";
import { registry } from "@web/core/registry";
import { props, t } from "@odoo/owl";

export class WebsiteBackgroundOption extends BaseOptionComponent {
    static id = "website_background_option";
    static template = "website.WebsiteBackgroundOption";
    static components = {
        ...BackgroundOption.components,
        ParallaxOption,
        BgBlurOption,
    };
    props = props({
        ...backgroundOptionProps,
        withColors: t.boolean().optional(true),
        withImages: t.boolean().optional(true),
        withColorCombinations: t.boolean().optional(true),
        withVideos: t.boolean().optional(false),
    });
    setup() {
        super.setup();
        const { showColorFilter } = useBackgroundOption(this.isActiveItem);
        this.showColorFilter = () => showColorFilter() || this.isActiveItem("toggle_bg_video_id");
        // ":scope > .s_parallax_bg" is kept for compatibility.
        const parallaxBgSelector =
            ":scope > .s_parallax_bg, :scope > .s_parallax_bg_wrap > .s_parallax_bg";
        this.websiteBgOptionDomState = useDomState((el) => {
            // Only search for .s_parallax_bg that are direct children
            const parallaxBgEl = el.querySelector(parallaxBgSelector);
            const target = parallaxBgEl || el;
            return {
                applyTo: parallaxBgEl ? parallaxBgSelector : "",
                hasBgMedia:
                    target.style.backgroundImage.includes("url(") ||
                    el.classList.contains("o_background_video"),
            };
        });
    }
}

registry.category("website-options").add(WebsiteBackgroundOption.id, WebsiteBackgroundOption);
