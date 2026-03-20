import { _t } from "@web/core/l10n/translation";
import EventAdditionalTourSteps from "@event/js/tours/event_steps";

import { markup } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { insertSnippet } from '@website/js/tours/tour_utils';

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
            ...insertSnippet({
                id: "s_image_text",
                name: "Image - Text",
                groupName: "Content",
            }),
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
