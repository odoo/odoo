/** @odoo-module **/

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
                position: 'bottom',
            }, {
                trigger: '.o_edit_website_container a',
                content: markup(_t("With the Edit button, you can <b>customize</b> the web page visitors will see when registering.")),
                position: 'bottom',
            }, {
                trigger: '#oe_snippets.o_loaded div[name="Image - Text"] .oe_snippet_thumbnail',
                content: markup(_t("<b>Drag and Drop</b> this snippet below the event title.")),
                position: 'bottom',
                run: 'drag_and_drop_native iframe #o_wevent_event_main_col',
            }, {
                trigger: 'button[data-action="save"]',
                content: markup(_t("Don't forget to click <b>save</b> when you're done.")),
                position: 'bottom',
            }, {
                trigger: '.o_menu_systray_item .o_switch_danger_success',
                extra_trigger: 'iframe body:not(.editor_enable) .o_wevent_event',
                content: markup(_t("Looking great! Let's now <b>publish</b> this page so that it becomes <b>visible</b> on your website!")),
                position: 'bottom',
            }, {
                trigger: '.o_website_edit_in_backend > a',
                extra_trigger: 'iframe .o_wevent_event',
                content: _t("This shortcut will bring you right back to the event form."),
                position: 'bottom'
            }];
    }
});

export default EventAdditionalTourSteps;
