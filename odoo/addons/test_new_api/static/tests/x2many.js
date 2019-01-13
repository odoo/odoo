odoo.define('web.test.x2many', function (require) {
    'use strict';

    var tour = require("web_tour.tour");
    var inc;

    tour.register('widget_x2many', {
        url: '/web?debug=assets#action=test_new_api.action_discussions',
        test: true,
    }, [
    /////////////////////////////////////////////////////////////////////////////////////////////
    // Discussions
    /////////////////////////////////////////////////////////////////////////////////////////////
    {
        content: "wait web client",
        trigger: '.breadcrumb:contains(Discussions)',
    }, { // create test discussion
        content: "create new discussion",
        trigger: 'button.o_list_button_add',
    }, {
        content: "insert content",
        trigger: 'input.o_required_modifier',
        run: 'text test',
    }, { // try to add a user with one2many form
        content: "click on moderator one2many drop down",
        trigger: 'tr:contains(Moderator) .o_input_dropdown > input',
        run: 'click',
    }, {
        content: "click on 'Create and Edit...'",
        trigger: '.ui-autocomplete .o_m2o_dropdown_option:last',
    }, {
        content: "insert a name into the modal form",
        trigger: 'input.o_field_widget.o_required_modifier:first',
        extra_trigger: '.modal:visible',
        run: function (action_helper) {
            action_helper.text('user_test_' + (inc = new Date().getTime()));
        }
    }, {
        content: "insert an email into the modal form",
        extra_trigger: 'input.o_field_widget.o_required_modifier:propValueContains(user_test)',
        trigger: 'input.o_field_widget.o_required_modifier:eq(1)',
        run: function (action_helper) {
            action_helper.text('user_test_' + inc + '@test');
        }
    }, {
        content: "save the modal content and create the new moderator",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'input.o_field_widget.o_required_modifier:propValueContains(@test)',
    }, {
        content: "check if the modal is saved",
        trigger: 'tr:contains(Moderator) .o_field_many2one input:propValueContains(user_test)',
        run: function () {}, // it's a check
    }, {
        content: "check the onchange from the o2m to the m2m",
        trigger: '.o_content:has(.tab-pane:eq(2) .o_field_widget tbody tr td:contains(user_test))',
        run: function () {}, // it's a check
    }, { // add ourself as participant
        content: "change tab to Participants",
        trigger: '[data-toggle="tab"]:contains(Participants)'
    }, {
        content: "click to add participants",
        trigger: '.tab-pane:eq(2).active .o_field_x2many_list_row_add a'
    }, {
        content: "select Admin",
        trigger: 'tr:has(td:containsExact(Mitchell Admin)) .o_list_record_selector input[type="checkbox"]'
    }, {
        content: "save selected participants",
        trigger: '.o_select_button',
        extra_trigger: 'tr:has(td:containsExact(Mitchell Admin)) .o_list_record_selector input[type="checkbox"]:propChecked',
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: '.tab-pane:eq(2) .o_field_widget tbody tr:has(td:containsExact(Mitchell Admin))',
    }, { // edit
        content: "edit discussion",
        trigger: 'button.o_form_button_edit',
    }, { // add message a
        content: "Select First Tab",
        trigger: 'a[role=tab]:first',
    }, {
        content: "create new message a",
        trigger: '.tab-pane:eq(0) .o_field_x2many_list_row_add a'
    }, {
        content: "insert body a",
        trigger: '.modal-body textarea:first',
        run: 'text a',
    }, {
        content: "save new message a",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: '.modal-body textarea:first:propValue(a)',
    }, { // add message b
        content: "create new message b",
        trigger: '.tab-pane:eq(0) .o_field_x2many_list_row_add a',
        extra_trigger: '.o_web_client:has(textarea[name="message_concat"]:propValue([test] Mitchell Admin:a))',
    }, {
        content: "insert body b",
        trigger: 'textarea[name="body"]:first',
        run: 'text b',
    }, {
        content: "save new message b",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'textarea[name="body"]:first:propValue(b)',
    }, { // change content to trigger on change
        content: "insert content",
        trigger: 'input.o_required_modifier',
        extra_trigger: 'textarea[name="message_concat"]:first:propValue([test] Mitchell Admin:a\n[test] Mitchell Admin:b)',
        run: 'text test_trigger',
    }, {
        content: "blur the content field",
        trigger: 'input.o_required_modifier',
        run: 'text test_trigger',
    }, {
        content: "check onchange",
        trigger: 'textarea[name="message_concat"]:first:propValue([test_trigger] Mitchell Admin:a\n[test_trigger] Mitchell Admin:b)',
        run: function () {},
    }, { // change message b
        content: "edit message b",
        trigger: '.tab-pane:eq(0) .o_field_widget tbody tr td:containsExact(b)',
        extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2))) .tab-pane:eq(0) .o_field_widget tbody tr td:contains([test_trigger] )',
    }, {
        content: "change the body",
        trigger: 'textarea[name="body"]:first',
        run: 'text bbb',
    }, {
        content: "save changes",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'textarea[name="body"]:first:propValue(bbb)',
    }, { // add message c
        content: "create new message c",
        trigger: '.tab-pane:eq(0) .o_field_x2many_list_row_add a',
        extra_trigger: 'textarea[name="message_concat"]:propValue([test_trigger] Mitchell Admin:a\n[test_trigger] Mitchell Admin:bbb)',
    }, {
        content: "insert body",
        trigger: 'textarea[name="body"]:first',
        run: 'text c',
    }, {
        content: "save new message c",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'textarea[name="body"]:first:propValue(c)',
    }, { // add participants
        content: "change tab to Participants",
        trigger: '[data-toggle="tab"]:contains(Participants)',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2)',
    }, {
        content: "click to add participants",
        trigger: '.tab-pane:eq(2).active .o_field_x2many_list_row_add a',
    }, {
        content: "select Demo User",
        trigger: 'tr:has(td:containsExact(Marc Demo)) .o_list_record_selector input[type="checkbox"]',
    }, {
        content: "save selected participants",
        trigger: '.o_select_button',
        extra_trigger: 'tr:has(td:containsExact(Marc Demo)) .o_list_record_selector input[type="checkbox"]:propChecked',
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'body:not(:has(.tab-pane:eq(2) .o_field_widget tbody .o_data_row:eq(3))) .tab-pane:eq(2) .o_field_widget tbody .o_data_row:eq(2)',
    }, { // check saved data
        content: "check data 1",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2))',
        extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(3)))',
        run: function () {}, // it's a check
    }, {
        content: "check data 2",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_field_widget tr:has(td:containsExact(bbb)):has(td:containsExact([test_trigger] Mitchell Admin)))',
        run: function () {}, // it's a check
    }, {
        content: "check data 3",
        trigger: '.o_content:has(.tab-pane:eq(2) .o_field_widget tbody .o_data_row:eq(2))',
        extra_trigger: 'body:not(:has(.tab-pane:eq(2) .o_field_widget tbody .o_data_row:eq(3)))',
        run: function () {}, // it's a check
    }, { // edit
        content: "edit discussion",
        trigger: 'button.o_form_button_edit',
    }, {
        content: "change tab to Messages",
        trigger: '[data-toggle="tab"]:contains(Messages)',
        extra_trigger: '.o_form_editable',
    }, { // add message d
        content: "create new message d",
        trigger: '.tab-pane:eq(0) .o_field_x2many_list_row_add a',
        extra_trigger: 'a[data-toggle="tab"].active:contains(Messages)',
    }, {
        content: "insert body",
        trigger: 'textarea[name="body"]:first',
        run: 'text d',
    }, {
        content: "save new message d",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'textarea[name="body"]:first:propValue(d)',
    }, { // add message e
        content: "create new message e",
        trigger: '.tab-pane:eq(0) .o_field_x2many_list_row_add a',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody tr td:containsExact(d)',
    }, {
        content: "insert body",
        trigger: 'textarea[name="body"]:first',
        run: 'text e',
    }, {
        content: "save new message e",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'textarea[name="body"]:first:propValue(e)',
    }, { // change message a
        content: "edit message a",
        trigger: '.tab-pane:eq(0) .o_field_widget tbody tr td:containsExact(a)',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody tr td:containsExact(e)',
    }, {
        content: "change the body",
        trigger: 'textarea[name="body"]:first',
        run: 'text aaa',
    }, {
        content: "save changes",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'textarea[name="body"]:first:propValue(aaa)',
    }, { // change message e
        content: "edit message e",
        trigger: '.tab-pane:eq(0) .o_field_widget tbody tr td:containsExact(e)',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody tr td:contains(aaa)',
    }, {
        content: "open the many2one to select another user",
        trigger: '.o_input_dropdown > input',
        run: 'text Marc',
    }, {
        content: "select another user",
        trigger: '.ui-autocomplete li:contains(Marc Demo)',
        in_modal: false,
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_field_widget:contains([test_trigger] Marc Demo)',
        run: function () {}, // it's a check
    }, {
        content: "test one2many field not triggered onchange",
        trigger: 'textarea[name="message_concat"]:first:propValueContains([test_trigger] Mitchell Admin:e)',
        in_modal: false,
        run: function () {}, // don't change texarea content
    }, {
        content: "save changes",
        trigger: '.modal-footer button:contains(Save):contains(Close)'
    }, {
        content: "test one2many triggered the onchange on save for the line",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_field_widget tbody tr td.o_readonly_modifier:contains([test_trigger] Marc Demo))',
        run: function () {}, // it's a check
    }, {
        content: "test one2many triggered the onchange on save",
        trigger: 'textarea[name="message_concat"]:first:propValueContains([test_trigger] Marc Demo:e)',
        run: function () {}, // don't change texarea content
    }, { // remove
        content: "remove b",
        trigger: '.tab-pane:eq(0) .o_field_widget tbody tr:has(td:containsExact(bbb)) .o_list_record_remove',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody tr td:containsExact(aaa)',
    }, {
        content: "remove e",
        trigger: 'tr:has(td:containsExact(e)) .o_list_record_remove',
        extra_trigger: 'body:not(:has(tr:has(td:containsExact(bbb))))',
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'body:not(:has(tr:has(td:containsExact(e))))',
    }, { // check saved data
        content: "check data 4",
        trigger: '.o_content:not(:has(.tab-pane:eq(0) .o_field_widget tbody tr:has(.o_list_record_remove):eq(4)))',
        run: function () {}, // it's a check
    }, {
        content: "check data 5",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_field_widget tbody:has(tr td:containsExact(aaa)):has(tr td:containsExact(c)):has(tr td:containsExact(d)))',
        run: function () {}, // it's a check
    }, {
        content: "check data 6",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_field_widget tbody tr:has(td:containsExact([test_trigger] Mitchell Admin)):has(td:containsExact(aaa)))',
        run: function () {}, // it's a check
    }, {
        content: "check data 7",
        trigger: '.o_content:has(.tab-pane:eq(2) .o_field_widget tbody .o_data_row:eq(2))',
        extra_trigger: '.o_content:not(:has(.tab-pane:eq(2) .o_field_widget tbody tr[date-id]:eq(3)))',
        run: function () {}, // it's a check
    }, { // edit
        content: "edit discussion",
        trigger: 'button.o_form_button_edit',
    }, { // add message ddd
        content: "create new message ddd",
        trigger: '.tab-pane:eq(0) .o_field_x2many_list_row_add a',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody tr:has(td:containsExact(d))',
    }, {
        content: "select another user",
        trigger: '.o_field_many2one .o_input_dropdown > input',
        extra_trigger: 'body:has(.modal) .tab-pane:eq(0) .o_field_widget tbody tr:has(td:containsExact(d))',
        run: 'text Marc',
    }, {
        content: "select demo user",
        trigger: '.ui-autocomplete li a:contains(Marc Demo)',
        in_modal: false,
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_field_widget:contains([test_trigger] Marc Demo)',
        run: function () {}, // it's a check
    }, {
        content: "insert body",
        trigger: 'textarea[name="body"]:first',
        run: 'text ddd',
    }, {
        content: "save new message ddd",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'textarea[name="body"]:first:propValue(ddd)',
    }, { // trigger onchange
        content: "blur the one2many",
        trigger: 'input.o_required_modifier',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody:has(tr td:containsExact(ddd))',
    }, { // check onchange data
        content: "check data 8",
        trigger: 'textarea[name="message_concat"]:propValueContains([test_trigger] Mitchell Admin:aaa\n[test_trigger] Mitchell Admin:c\n[test_trigger] Mitchell Admin:d\n[test_trigger] Marc Demo:ddd)',
        run: function () {}, // don't change texarea content
    }, {
        content: "check data 9",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(3))',
        extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(4)))',
        run: function () {}, // it's a check
    }, { // cancel
        content: "cancel change",
        trigger: '.o_cp_buttons .o_form_button_cancel',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody:has(tr td:containsExact(ddd))',
        run: 'click',
    }, {
        content: "confirm cancel change",
        trigger: '.modal-footer button:contains(Ok)',
    },

    /////////////////////////////////////////////////////////////////////////////////////////////
    // Discussions 2
    /////////////////////////////////////////////////////////////////////////////////////////////

    {
        content: "switch to the second form view to test one2many with editable list (toggle menu dropdown)",
        trigger: 'nav .o_menu_sections .dropdown-toggle:containsExact(Discussions)',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2)',
    }, {
        content: "switch to the second form view to test one2many with editable list (open submenu)",
        trigger: 'nav .o_menu_sections .dropdown-item:contains(Discussions 2)',
    }, {
        content: "select previous created record",
        trigger: 'td:contains(test_trigger):last',
        extra_trigger: '.breadcrumb-item:containsExact(Discussions 2)',
    }, {
        content: "click on edit",
        trigger: '.o_cp_buttons .o_form_button_edit',
    }, {
        content: "edit content",
        trigger: 'input.o_required_modifier',
        extra_trigger: ".o_form_editable",
        run: 'text test_trigger2'
    }, {
        content: "click outside to trigger onchange",
        trigger: '.o_form_sheet',
    }, {
        content: "click on a field of the editable list to edit content",
        trigger: '.o_list_view .o_data_row:eq(1) td',
        extra_trigger: '.o_list_view:contains(test_trigger2)',
    }, {
        content: "change text value",
        trigger: 'textarea[name="body"]:first',
        run: 'text ccc'
    }, {
        content: "click on other field (trigger the line onchange)",
        trigger: '.o_list_view .o_field_many2one[name="author"] input',
        run: 'click'
    }, {
        content: "test one2many's line onchange",
        trigger: '.o_list_view .o_selected_row td:nth(3):contains(3)',
        run: function () {}, // don't blur the many2one
    }, {
        content: "open the many2one to select an other user",
        trigger: '.o_list_view .o_field_many2one[name="author"] .o_input_dropdown > input',
        run: 'text Marc',
    }, {
        content: "select an other user",
        trigger: '.ui-autocomplete li a:contains(Marc Demo)',
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_list_view td:contains([test_trigger2] Marc Demo)',
        run: function () {}, // don't blur the many2one
    }, {
        content: "change text value",
        trigger: 'textarea[name="body"]:first',
        run: 'text ccccc',
    }, { // check onchange
        content: "click outside to trigger one2many onchange",
        trigger: 'input.o_required_modifier',
        run: 'click'
    }, {
        content: "test one2many onchange",
        trigger: 'textarea[name="message_concat"]:first:propValueContains([test_trigger2] Marc Demo:ccccc)',
        run: function () {}, // don't change texarea content
    }, {
        content: "click outside to trigger one2many onchange",
        trigger: '.o_field_many2manytags .o_input_dropdown > input',
    }, {
        content: "add a tag",
        trigger: '.ui-autocomplete a:first',
    }, { // remove record
        content: "delete the last item in the editable list",
        trigger: '.o_list_view .o_data_row td.o_list_record_remove button:visible:last',
    }, {
        content: "test one2many onchange after delete",
        trigger: '.o_content:not(:has(textarea[name="message_concat"]:propValueContains(Mitchell Admin:d)))',
        run: function () {},
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'body:not(:has(tr:has(td:containsExact(d))))',
    }, { // check saved data
        content: "check data 10",
        trigger: '.o_field_text:containsExact([test_trigger2] Mitchell Admin:aaa\n[test_trigger2] Marc Demo:ccccc)',
        run: function () {}, // don't change texarea content
    }, {
        content: "check data 11",
        trigger: '.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(1)',
        extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2)))',
        run: function () {},
    }, { // edit
        content: "edit discussion",
        trigger: 'button.o_form_button_edit'
    }, { // add message eee
        content: "create new message eee",
        trigger: '.tab-pane:eq(0) .o_field_x2many_list_row_add a',
        extra_trigger: 'a[data-toggle="tab"].active:contains(Messages)',
    }, {
        content: "change text value",
        trigger: 'textarea[name="body"]:first',
        run: 'text eee'
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'textarea[name="body"]:first:propValueContains(eee)',
    }, { // check saved data
        content: "check data 12",
        trigger: '.o_field_text[name="message_concat"]:containsExact([test_trigger2] Mitchell Admin:aaa\n[test_trigger2] Marc Demo:ccccc\n[test_trigger2] Mitchell Admin:eee)',
        run: function () {}, // it's a check
    }, {
        content: "check data 13",
        trigger: '.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2)',
        extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(3)))',
        run: function () {}, // it's a check
    },

    /////////////////////////////////////////////////////////////////////////////////////////////
    // Discussions 3
    /////////////////////////////////////////////////////////////////////////////////////////////

    {
        content: "switch to the third form view to test onchange changing one2many (toggle menu dropdown)",
        trigger: 'nav .o_menu_sections .dropdown-toggle:containsExact(Discussions)',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2)',
    }, {
        content: "switch to the thied form view to test onchange changing one2many (open submenu)",
        trigger: 'nav .o_menu_sections .dropdown-item:contains(Discussions 3)',
    }, {
        content: "wait web client",
        trigger: '.breadcrumb:contains(Discussions 3)',
    }, {
        content: "create new discussion",
        trigger: 'button.o_list_button_add',
    }, {
        content: "set discussion title to generate dummy message",
        trigger: 'input.o_required_modifier',
        run:     'text {generate_dummy_message}',
    }, {
        content: "check new dummy message happened",
        trigger: '.o_field_widget[name=messages] .o_data_row .o_list_number:containsExact(13)',
        extra_trigger: '.o_field_widget[name=important_messages] .o_data_row .o_list_number:containsExact(13)',
        run: function () {}, // it's a check
    }, {
        content: "check field not in embedded view received correctly",
        trigger: '.o_field_widget[name=messages] .o_data_row input[type="checkbox"]:propChecked',
        run: function () {}, // it's a check
    }, {
        content: "empty discussion title",
        trigger: 'input.o_required_modifier',
        run:     'text removed_title',
    }, {
        content: "onchange happened",
        trigger: '.o_field_widget[name=messages] .o_data_row td:contains([removed_title])',
        run: function () {}, // it's a check
    }, {
        content: "set discussion title to generate dummy message",
        trigger: 'input.o_required_modifier',
        run:     'text {generate_dummy_message}',
    }, {
        content: "chuck update and new dummy message happened",
        trigger: '.o_field_widget[name=messages] .o_data_row .o_list_number:containsExact(22)',
        extra_trigger: '.o_field_widget[name=important_messages] .o_data_row .o_list_number:containsExact(22)',
        run: function () {}, // it's a check
    }, { // cancel
        content: "cancel change",
        trigger: '.o_cp_buttons .o_form_button_cancel',
        run: 'click',
    }, {
        content: "confirm cancel change",
        trigger: '.modal-footer button:contains(Ok)',
    }]);
});
