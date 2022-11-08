odoo.define('website_event.event_steps', function (require) {
"use strict";

const {_t} = require('web.core');
const {Markup} = require('web.utils');

var EventAdditionalTourSteps = require('event.event_steps');

EventAdditionalTourSteps.include({

    init: function() {
        this._super.apply(this, arguments);
    },

    _get_website_event_steps: function () {
        this._super.apply(this, arguments);
        return [{
                trigger: '.o_event_form_view button[title="Unpublished"]',
                content: Markup(_t("Use this <b>shortcut</b> to easily access your event web page.")),
                position: 'bottom',
            }, {
                trigger: '.o_edit_website_container a',
                content: Markup(_t("With the Edit button, you can <b>customize</b> the web page visitors will see when registering.")),
                position: 'bottom',
            }, {
                trigger: '#oe_snippets.o_loaded div[name="Image - Text"] .oe_snippet_thumbnail',
                content: Markup(_t("<b>Drag and Drop</b> this snippet below the event title.")),
                position: 'bottom',
                run: 'drag_and_drop iframe #o_wevent_event_main_col',
            }, {
                trigger: 'button[data-action="save"]',
                content: Markup(_t("Don't forget to click <b>save</b> when you're done.")),
                position: 'bottom',
            }, {
                trigger: '.o_menu_systray_item .o_switch_danger_success',
                extra_trigger: 'iframe body:not(.editor_enable) .o_wevent_event',
                content: Markup(_t("Looking great! Let's now <b>publish</b> this page so that it becomes <b>visible</b> on your website!")),
                position: 'bottom',
            }, {
                trigger: '.o_website_edit_in_backend > a',
                extra_trigger: 'iframe .o_wevent_event',
                content: _t("This shortcut will bring you right back to the event form."),
                position: 'bottom'
            }];
    }
});

return EventAdditionalTourSteps;

});
