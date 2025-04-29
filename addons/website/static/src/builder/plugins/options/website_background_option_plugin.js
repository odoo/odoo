import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
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
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_BEFORE } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";

class WebsiteBackgroundOptionPlugin extends Plugin {
    static id = "websiteOption";
    sectionSelector = "section";
    carouselApplyTo = ":scope > .carousel:not(.s_carousel_cards)";
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_BEFORE, {
                OptionComponent: WebsiteBackgroundOption,
                selector: this.sectionSelector,
                applyTo: this.carouselApplyTo,
                props: {
                    withColors: true,
                    withImages: true,
                    withVideos: true,
                    withShapes: true,
                    withColorCombinations: true,
                },
            }),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, {
                OptionComponent: WebsiteBackgroundOption,
                selector: BOTH_BG_COLOR_IMAGE_SELECTOR,
                exclude: BOTH_BG_COLOR_IMAGE_EXCLUDE,
                props: {
                    withColors: true,
                    withImages: true,
                    withVideos: true,
                    withShapes: true,
                    withColorCombinations: true,
                },
            }),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, {
                OptionComponent: WebsiteBackgroundOption,
                selector: ONLY_BG_COLOR_SELECTOR,
                exclude: ONLY_BG_COLOR_EXCLUDE,
                props: {
                    withColors: true,
                    withImages: false,
                    withColorCombinations: true,
                },
            }),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, {
                OptionComponent: WebsiteBackgroundOption,
                selector: ONLY_BG_IMAGE_SELECTOR,
                exclude: ONLY_BG_IMAGE_EXLUDE,
                props: {
                    withColors: false,
                    withImages: true,
                    withVideos: true,
                    withShapes: true,
                    withColorCombinations: false,
                },
            }),
        ],
        mark_color_level_selector_params: [
            { selector: this.sectionSelector, applyTo: this.carouselApplyTo },
            { selector: BOTH_BG_COLOR_IMAGE_SELECTOR, exclude: BOTH_BG_COLOR_IMAGE_EXCLUDE },
            { selector: ONLY_BG_COLOR_SELECTOR, exclude: ONLY_BG_COLOR_EXCLUDE },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteBackgroundOptionPlugin.id, WebsiteBackgroundOptionPlugin);
