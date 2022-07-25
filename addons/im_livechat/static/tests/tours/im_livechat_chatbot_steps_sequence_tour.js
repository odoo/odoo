/** @odoo-module */

import tour from "web_tour.tour";

const commonSteps = [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="im_livechat.menu_livechat_root"]',
}, {
    trigger: 'button[data-menu-xmlid="im_livechat.livechat_config"]',
}, {
    trigger: 'a[data-menu-xmlid="im_livechat.chatbot_config"]',
}, {
    trigger: '.o_list_button_add',
}, {
    trigger: 'input[name="title"]',
    run: 'text Test Chatbot Sequence'
}, {
    trigger: 'div[name="script_step_ids"] .o_field_x2many_list_row_add a'
}, {
    trigger: 'textarea[name="message"]',
    run: 'text Step 1'
}, {
    trigger: 'button:contains("Save & New")'
}, {
    trigger: 'tr:contains("Step 1")',
    in_modal: false,
    run: () => {}
}, {
    trigger: 'textarea[name="message"]',
    run: 'text Step 2'
}, {
    trigger: 'button:contains("Save & New")'
}, {
    trigger: 'tr:contains("Step 2")',
    in_modal: false,
    run: () => {}
}, {
    trigger: 'textarea[name="message"]',
    run: 'text Step 3'
}];


/**
 * Simply create a few steps in order to check the sequences.
 */
 tour.register('im_livechat_chatbot_steps_sequence_tour', {
    test: true,
    url: '/web',
}, [
    ...commonSteps, {
    trigger: 'button:contains("Save & Close")'
}, {
    trigger: 'body.o_web_client:not(.modal-open)',
    run() {},
}, ...tour.stepUtils.discardForm()
]);

/**
 * Same as above, with an extra drag&drop at the end.
 */
tour.register('im_livechat_chatbot_steps_sequence_with_move_tour', {
    test: true,
    url: '/web',
}, [
    ...commonSteps, {
    trigger: 'button:contains("Save & New")'
}, {
    trigger: 'tr:contains("Step 3")',
    in_modal: false,
    run: () => {}
}, {
    trigger: 'textarea[name="message"]',
    run: 'text Step 4'
}, {
    trigger: 'button:contains("Save & New")'
}, {
    trigger: 'tr:contains("Step 4")',
    in_modal: false,
    run: () => {}
}, {
    trigger: 'textarea[name="message"]',
    run: 'text Step 5'
}, {
    trigger: 'button:contains("Save & Close")'
}, {
    trigger: 'body.o_web_client:not(.modal-open)',
    run: () => {}
}, {
    trigger: 'tr:contains("Step 5") .o_row_handle',
    run: () => {
        // move 'step 5' between 'step 1' and 'step 2'
        // tried to use to built-in 'drag_and_drop' action but it doesn't work here
        // somehow it only registers the move if 2 separate 'mousemove' events are triggered
        const $element = $('tr:contains("Step 5") .o_row_handle');
        const elementCenter = $element.offset();
        elementCenter.left += $element.outerWidth() / 2;
        elementCenter.top += $element.outerHeight() / 2;
        const $to = $('tr:eq(1)');
        const toCenter = $to.offset();
        toCenter.left += $to.outerWidth() / 2;
        toCenter.top += $to.outerHeight() / 2;

        $element.trigger($.Event("mouseenter"));
        $element.trigger($.Event("mousedown", {
            which: 1,
            pageX: elementCenter.left,
            pageY: elementCenter.top
        }));

        $element.trigger($.Event("mousemove", {
            which: 1,
            pageX: toCenter.left - 1,
            pageY: toCenter.top - 1
        }));

        $element.trigger($.Event("mousemove", {
            which: 1,
            pageX: toCenter.left,
            pageY: toCenter.top
        }));

        $element.trigger($.Event("mouseup", {
            which: 1,
            pageX: toCenter.left,
            pageY: toCenter.top
        }));
    }
}, {
    trigger: 'div[name="script_step_ids"] .o_field_x2many_list_row_add a'
}, {
    trigger: 'textarea[name="message"]',
    run: 'text Step 6'
}, {
    trigger: 'button:contains("Save & Close")'
}, {
    trigger: 'body.o_web_client:not(.modal-open)',
    run: () => {}
}, {
    trigger: 'tr:contains("Step 6")',
    in_modal: false,
    run: () => {}
}, ...tour.stepUtils.discardForm(),
]);
