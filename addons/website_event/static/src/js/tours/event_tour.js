import { _t } from "@web/core/l10n/translation";
import EventAdditionalTourSteps from "@event/js/tours/event_steps";

import { markup } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(EventAdditionalTourSteps.prototype, {

    _get_website_event_steps() {
        return [
            ...super._get_website_event_steps(), {
                trigger: '.o_event_form_view button[title="Unpublished"]',
                content: markup(_t("Use this <b>shortcut</b> to easily access your event web page.")),
                tooltipPosition: 'bottom',
                run: "click",
            }, {
                trigger: '.o_edit_website_container a',
                content: markup(_t("With the Edit button, you can <b>customize</b> the web page visitors will see when registering.")),
                tooltipPosition: 'bottom',
                run: "click",
            },
            {
                trigger: ".o_builder_sidebar_open",
            },
            {
                content: markup(_t("Click on the <b>Content</b> category.")),
                trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="Content"].o_draggable .o_snippet_thumbnail_area`,
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                content: markup(_t("Click on the <b>Image - Text</b> building block.")),
                trigger: `.modal .show:iframe .o_snippet_preview_wrap[data-snippet-id="s_image_text"]:not(.d-none)`,
                tooltipPosition: "top",
                run: "click",
            },
            {
                trigger: ".o_website_preview :iframe:not(:has(.o_loading_screen))",
            },
            {
                trigger: 'button[data-action="save"]',
                content: markup(_t("Don't forget to click <b>save</b> when you're done.")),
                tooltipPosition: 'bottom',
                run: "click",
            },
            {
                trigger: ":iframe body:not(.editor_enable) .o_wevent_event",
            },
            {
                trigger: '.o_menu_systray_item.o_website_publish_container a',
                content: markup(_t("Looking great! Let's now <b>publish</b> this page so that it becomes <b>visible</b> on your website!")),
                tooltipPosition: 'bottom',
                run: "click",
            },
            {
                trigger: ":iframe .o_wevent_event",
            },
            {
                trigger: '.o_website_edit_in_backend > a',
                content: _t("This shortcut will bring you right back to the event form."),
                tooltipPosition: 'bottom',
                run: "click",
            }];
    }
});
