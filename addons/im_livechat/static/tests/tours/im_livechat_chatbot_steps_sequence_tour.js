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
    trigger: 'input[id="title"]',
    run: 'text Test Chatbot Sequence'
}, {
    trigger: 'div[name="script_step_ids"] .o_field_x2many_list_row_add a'
}, {
    trigger: 'textarea#message',
    run: 'text Step 1'
}, {
    trigger: 'button:contains("Save & New")'
}, {
    trigger: 'tr:contains("Step 1")',
    in_modal: false,
    run: () => {}
}, {
    trigger: 'textarea#message',
    run: 'text Step 2'
}, {
    trigger: 'button:contains("Save & New")'
}, {
    trigger: 'tr:contains("Step 2")',
    in_modal: false,
    run: () => {}
}, {
    trigger: 'textarea#message',
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
    trigger: 'textarea#message',
    run: 'text Step 4'
}, {
    trigger: 'button:contains("Save & New")'
}, {
    trigger: 'tr:contains("Step 4")',
    in_modal: false,
    run: () => {}
}, {
    trigger: 'textarea#message',
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
        const from = document.querySelector('div[name="script_step_ids"] tr:nth-child(5) .o_row_handle');
        const fromPosition = from.getBoundingClientRect();
        fromPosition.x += from.offsetWidth / 2;
        fromPosition.y += from.offsetHeight / 2;

        const to = document.querySelector('div[name="script_step_ids"] tr:nth-child(2) .o_row_handle');
        from.dispatchEvent(new Event("mouseenter", { bubbles: true }));
        from.dispatchEvent(new MouseEvent("mousedown", {
            bubbles: true,
            which: 1,
            button: 0,
            clientX: fromPosition.x,
            clientY: fromPosition.y}));
        from.dispatchEvent(new Event("mousemove", { bubbles: true }));
        to.dispatchEvent(new Event("mouseenter", { bubbles: true }));
        from.dispatchEvent(new Event("mouseup", { bubbles: true }));
    }
}, {
    trigger: 'div[name="script_step_ids"] .o_field_x2many_list_row_add a'
}, {
    trigger: 'textarea#message',
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
