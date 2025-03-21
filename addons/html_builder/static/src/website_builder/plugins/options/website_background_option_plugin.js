import { WebsiteBackgroundOption } from "@html_builder/website_builder/plugins/options/background_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    BOTH_BG_COLOR_IMAGE_EXCLUDE,
    BOTH_BG_COLOR_IMAGE_SELECTOR,
    ONLY_BG_COLOR_EXCLUDE,
    ONLY_BG_COLOR_SELECTOR,
    ONLY_BG_IMAGE_EXLUDE,
    ONLY_BG_IMAGE_SELECTOR,
} from "./utils";

class WebsiteBackgroundOptionPlugin extends Plugin {
    static id = "websiteOption";
    resources = {
        builder_options: [
            {
                OptionComponent: WebsiteBackgroundOption,
                selector: "section",
                applyTo: ":scope > .carousel:not(.s_carousel_cards)",
                props: {
                    withColors: true,
                    withImages: true,
                    withVideos: true,
                    withShapes: true,
                    withGradient: true,
                    withColorCombinations: true,
                },
            },
            {
                OptionComponent: WebsiteBackgroundOption,
                selector: BOTH_BG_COLOR_IMAGE_SELECTOR,
                exclude: BOTH_BG_COLOR_IMAGE_EXCLUDE,
                props: {
                    withColors: true,
                    withImages: true,
                    withVideos: true,
                    withShapes: true,
                    withGradient: true,
                    withColorCombinations: true,
                },
            },
            {
                OptionComponent: WebsiteBackgroundOption,
                selector: ONLY_BG_COLOR_SELECTOR,
                exclude: ONLY_BG_COLOR_EXCLUDE,
                props: {
                    withColors: true,
                    withImages: false,
                    withGradient: true,
                    withColorCombinations: true,
                },
            },
            {
                OptionComponent: WebsiteBackgroundOption,
                selector: ONLY_BG_IMAGE_SELECTOR,
                exclude: ONLY_BG_IMAGE_EXLUDE,
                props: {
                    withColors: false,
                    withImages: true,
                    withVideos: true,
                    withShapes: true,
                },
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteBackgroundOptionPlugin.id, WebsiteBackgroundOptionPlugin);
