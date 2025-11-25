import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    BOTH_BG_COLOR_IMAGE_EXCLUDE,
    BOTH_BG_COLOR_IMAGE_SELECTOR,
    ONLY_BG_COLOR_EXCLUDE,
    ONLY_BG_COLOR_SELECTOR,
    ONLY_BG_IMAGE_EXCLUDE,
    ONLY_BG_IMAGE_SELECTOR,
} from "./utils";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_BEFORE } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";

export class WebsiteBackgroundCarouselOption extends BaseWebsiteBackgroundOption {
    static selector = "section";
    static applyTo = ":scope > .carousel:not(.s_carousel_cards)";
    static defaultProps = {
        withColors: true,
        withImages: true,
        withVideos: true,
        withShapes: true,
        withColorCombinations: true,
    };
}

export class WebsiteBackgroundBGColorImageOption extends BaseWebsiteBackgroundOption {
    static selector = BOTH_BG_COLOR_IMAGE_SELECTOR;
    static exclude = BOTH_BG_COLOR_IMAGE_EXCLUDE;
    static defaultProps = {
        withColors: true,
        withImages: true,
        withVideos: true,
        withShapes: true,
        withColorCombinations: true,
    };
}
export class WebsiteBackgroundBGColorOption extends BaseWebsiteBackgroundOption {
    static selector = ONLY_BG_COLOR_SELECTOR;
    static exclude = ONLY_BG_COLOR_EXCLUDE;
    static defaultProps = {
        withColors: true,
        withImages: false,
        withColorCombinations: true,
    };
}
export class WebsiteBackgroundOnlyBGImageOption extends BaseWebsiteBackgroundOption {
    static selector = ONLY_BG_IMAGE_SELECTOR;
    static exclude = ONLY_BG_IMAGE_EXCLUDE;
    static defaultProps = {
        withColors: false,
        withImages: true,
        withVideos: true,
        withShapes: true,
        withColorCombinations: false,
    };
}

class WebsiteBackgroundOptionPlugin extends Plugin {
    static id = "websiteOption";
    carouselApplyTo = ":scope > .carousel:not(.s_carousel_cards)";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_BEFORE, WebsiteBackgroundCarouselOption),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, WebsiteBackgroundBGColorImageOption),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, WebsiteBackgroundBGColorOption),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, WebsiteBackgroundOnlyBGImageOption),
        ],
        mark_color_level_selector_params: [
            {
                selector: WebsiteBackgroundCarouselOption.selector,
                applyTo: WebsiteBackgroundCarouselOption.applyTo,
            },
            {
                selector: WebsiteBackgroundBGColorImageOption.selector,
                exclude: WebsiteBackgroundBGColorImageOption.exclude,
            },
            {
                selector: WebsiteBackgroundBGColorOption.selector,
                exclude: WebsiteBackgroundBGColorOption.exclude,
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteBackgroundOptionPlugin.id, WebsiteBackgroundOptionPlugin);
