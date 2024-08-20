/** @odoo-module **/

import {
    MultipleItems,
    Box,
    SnippetOption,
} from "@web_editor/js/editor/snippets.options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";
import {
    websiteRegisterBackgroundOptions,
} from "@website/js/editor/snippets.options";

export class MediaItemLayoutOption extends SnippetOption {

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Change the media item layout.
     *
     * @see this.selectClass for parameters
     */
    layout(previewMode, widgetValue, params) {
        const $image = this.$target.find('.s_media_list_img_wrapper');
        const $content = this.$target.find('.s_media_list_body');

        for (const possibleValue of params.possibleValues) {
            $image.removeClass(`col-lg-${possibleValue}`);
            $content.removeClass(`col-lg-${12 - possibleValue}`);
        }
        $image.addClass(`col-lg-${widgetValue}`);
        $content.addClass(`col-lg-${12 - widgetValue}`);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'layout': {
                const $image = this.$target.find('.s_media_list_img_wrapper');
                for (const possibleValue of params.possibleValues) {
                    if ($image.hasClass(`col-lg-${possibleValue}`)) {
                        return possibleValue;
                    }
                }
            }
        }
        return super._computeWidgetState(...arguments);
    }
}

registerWebsiteOption("Media List (Multiple items)", {
    Class: MultipleItems,
    template: "website.s_media_list_option_add_media",
    selector: ".s_media_list",
}, { sequence: 24 });
websiteRegisterBackgroundOptions("Media List (background)", {
    selector: ".s_media_list_item",
    target: "> .row",
    withColors: true,
    withImages: false,
    withColorCombinations: true,
    withGradients: true,
});
registerWebsiteOption("Media List (border & shadow)", {
    Class: Box,
    template: "website.card_color_border_shadow",
    selector: ".s_media_list_item",
    target: "> .row",
});
registerWebsiteOption("Media List (layout)", {
    Class: SnippetOption,
    template: "website.s_media_list_option_layout",
    selector: ".s_media_list_item",
    target: "> .row",
});
registerWebsiteOption("Media List (item layout)", {
    Class: MediaItemLayoutOption,
    template: "website.s_media_list_option_item_layout",
    selector: ".s_media_list_item",
});
registerWebsiteOption("Media List (vertical alignment)", {
    Class: SnippetOption,
    template: "website.s_media_list_option_vertical_alignment",
    selector: ".s_media_list_item",
    target: "> .row",
});

