odoo.define('web.test.x2many', function (require) {
    'use strict';

    var tour = require("web_tour.tour");
    var inc;

    tour.register('widget_x2many', {
        url: '/web?debug=assets#action=test_new_api.action_discussions',
        test: true,
    }, [{
        content: "wait web client",
        trigger: '.breadcrumb:contains(Discussions)',
    }, { // create test discussion
        content: "create new discussion",
        trigger: 'button.o_list_button_add',
    }, {
        content: "insert content",
        trigger: 'input.o_form_required',
        run: 'text test',
    }, { // try to add a user with one2many form
        content: "click on moderator one2many drop down",
        trigger: 'tr:contains(Moderator) .o_form_input_dropdown > input',
        run: 'click',
    }, {
        content: "click on 'Create and Edit...'",
        trigger: '.ui-autocomplete .o_m2o_dropdown_option:last',
    }, {
        content: "insert a name into the modal form",
        trigger: 'input.o_form_field.o_form_required:first',
        extra_trigger: '.modal:visible',
        run: function (action_helper) {
            action_helper.text('user_test_' + (inc = new Date().getTime()));
        }
    }, {
        content: "insert an email into the modal form",
        extra_trigger: 'input.o_form_field.o_form_required:propValueContains(user_test)',
        trigger: 'input.o_form_field.o_form_required:eq(1)',
        run: function (action_helper) {
            action_helper.text('user_test_' + inc + '@test');
        }
    }, {
        content: "save the modal content and create the new moderator",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: 'input.o_form_field.o_form_required:propValueContains(@test)',
    }, {
        content: "check if the modal is saved",
        trigger: 'tr:contains(Moderator) .o_form_field_many2one input:propValueContains(user_test)',
        run: function () {}, // it's a check
    }, {
        content: "check the onchange from the o2m to the m2m",
        trigger: '.o_content:has(.tab-pane:eq(2) .o_form_field tbody tr td:contains(user_test))',
        run: function () {}, // it's a check
    }, { // add ourself as participant
        content: "change tab to Participants",
        trigger: '[data-toggle="tab"]:contains(Participants)'
    }, {
        content: "click to add participants",
        trigger: '.tab-pane:eq(2).active .o_form_field_x2many_list_row_add a'
    }, {
        content: "select Admin",
        trigger: 'tr:has(td:containsExact(Administrator)) .o_list_record_selector input[type="checkbox"]'
    }, {
        content: "save selected participants",
        trigger: '.o_select_button',
        extra_trigger: 'tr:has(td:containsExact(Administrator)) .o_list_record_selector input[type="checkbox"]:propChecked',
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: '.tab-pane:eq(2) .o_form_field tbody tr:has(td:containsExact(Administrator))',
    }, { // edit
        content: "edit discussion",
        trigger: 'button.o_form_button_edit',
    }, { // add message a
        content: "Select First Tab",
        trigger: 'a[role=tab]:first',
    }, {
        content: "create new message a",
        trigger: '.tab-pane:eq(0) .o_form_field_x2many_list_row_add a'
    }, {
        content: "insert body a",
        trigger: '.modal-body .o_form_textarea textarea:first',
        run: 'text a',
    }, {
        content: "save new message a",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: '.modal-body .o_form_textarea textarea:first:propValue(a)',
    }, { // add message b
        content: "create new message b",
        trigger: '.tab-pane:eq(0) .o_form_field_x2many_list_row_add a',
        extra_trigger: '.o_web_client:has(.o_form_textarea[name="message_concat"] textarea:propValue([test] Administrator:a))',
    }, {
        content: "insert body b",
        trigger: '.o_form_textarea[name="body"] textarea:first',
        run: 'text b',
    }, {
        content: "save new message b",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: '.o_form_textarea[name="body"] textarea:first:propValue(b)',
    }, { // change content to trigger on change
        content: "insert content",
        trigger: 'input.o_form_required',
        extra_trigger: '.o_form_textarea[name="message_concat"] textarea:first:propValue([test] Administrator:a\n[test] Administrator:b)',
        run: 'text test_trigger',
    }, {
        content: "blur the content field",
        trigger: 'input.o_form_required',
        run: 'text test_trigger',
    }, {
        content: "check onchange",
        trigger: '.o_form_textarea[name="message_concat"] textarea:first:propValue([test_trigger] Administrator:a\n[test_trigger] Administrator:b)',
        run: function () {},
    // FIXME: can't edit a not yet saved o2m record for now (problem 1)
    // }, { // change message b
    //     content: "edit message b",
    //     trigger: '.tab-pane:eq(0) .o_form_field tbody tr td:containsExact(b)',
    //     extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(2))) .tab-pane:eq(0) .o_form_field tbody tr td:contains([test_trigger] )',
    // }, {
    //     content: "change the body",
    //     trigger: '.o_form_textarea[name="body"] textarea:first',
    //     run: 'text bbb',
    // }, {
    //     content: "save changes",
    //     trigger: '.modal-footer button:contains(Save):first',
    //     extra_trigger: '.o_form_textarea[name="body"] textarea:first:propValue(bbb)',
    }, { // add message c
        content: "create new message c",
        trigger: '.tab-pane:eq(0) .o_form_field_x2many_list_row_add a',
        // extra_trigger: 'textarea[name="message_concat"]:propValue([test_trigger] Administrator:a\n[test_trigger] Administrator:bbb)', // FIXME (problem 1)
        extra_trigger: '.o_form_textarea[name="message_concat"] textarea:propValue([test_trigger] Administrator:a\n[test_trigger] Administrator:b)',
    }, {
        content: "insert body",
        trigger: '.o_form_textarea[name="body"] textarea:first',
        run: 'text c',
    }, {
        content: "save new message c",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: '.o_form_textarea[name="body"] textarea:first:propValue(c)',
    }, { // add participants
        content: "change tab to Participants",
        trigger: '[data-toggle="tab"]:contains(Participants)',
        extra_trigger: '.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(2)',
    }, {
        content: "click to add participants",
        trigger: '.tab-pane:eq(2).active .o_form_field_x2many_list_row_add a',
    }, {
        content: "select Demo User",
        trigger: 'tr:has(td:containsExact(Demo User)) .o_list_record_selector input[type="checkbox"]',
    }, {
        content: "save selected participants",
        trigger: '.o_select_button',
        extra_trigger: 'tr:has(td:containsExact(Demo User)) .o_list_record_selector input[type="checkbox"]:propChecked',
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'body:not(:has(.tab-pane:eq(2) .o_form_field tbody .o_data_row:eq(3))) .tab-pane:eq(2) .o_form_field tbody .o_data_row:eq(2)',
    }, { // check saved data
        content: "check data 1",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(2))',
        extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(3)))',
        run: function () {}, // it's a check
    }, {
        content: "check data 2",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tr:has(td:containsExact(b)):has(td:containsExact([test_trigger] Administrator)))',
        // trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tr:has(td:containsExact(bbb)):has(td:containsExact([test_trigger] Administrator)))', // FIXME (problem 1)
        run: function () {}, // it's a check
    }, {
        content: "check data 3",
        trigger: '.o_content:has(.tab-pane:eq(2) .o_form_field tbody .o_data_row:eq(2))',
        extra_trigger: 'body:not(:has(.tab-pane:eq(2) .o_form_field tbody .o_data_row:eq(3)))',
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
        trigger: '.tab-pane:eq(0) .o_form_field_x2many_list_row_add a',
        extra_trigger: 'li.active a[data-toggle="tab"]:contains(Messages)',
    }, {
        content: "insert body",
        trigger: '.o_form_textarea[name="body"] textarea:first',
        run: 'text d',
    }, {
        content: "save new message d",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: '.o_form_textarea[name="body"] textarea:first:propValue(d)',
    }, { // add message e
        content: "create new message e",
        trigger: '.tab-pane:eq(0) .o_form_field_x2many_list_row_add a',
        extra_trigger: '.tab-pane:eq(0) .o_form_field tbody tr td:containsExact(d)',
    }, {
        content: "insert body",
        trigger: '.o_form_textarea[name="body"] textarea:first',
        run: 'text e',
    }, {
        content: "save new message e",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: '.o_form_textarea[name="body"] textarea:first:propValue(e)',
    // FIXME: onchange don't work fine for now (problem 2), but this won't work anyway
    //        until problem 1 is solved
    // }, { // change message a
    //     content: "edit message a",
    //     trigger: '.tab-pane:eq(0) .o_form_field tbody tr td:containsExact(a)',
    //     extra_trigger: '.tab-pane:eq(0) .o_form_field tbody tr td:containsExact(e)',
    // }, {
    //     content: "change the body",
    //     trigger: '.o_form_textarea[name="body"] textarea:first',
    //     run: 'text aaa',
    // }, {
    //     content: "save changes",
    //     trigger: '.modal-footer button:contains(Save):first',
    //     extra_trigger: '.o_form_textarea[name="body"] textarea:first:propValue(aaa)',
    // }, { // change message e
    //     content: "edit message e",
    //     trigger: '.tab-pane:eq(0) .o_form_field tbody tr td:containsExact(e)',
    //     extra_trigger: '.tab-pane:eq(0) .o_form_field tbody tr td:contains(aaa)',
    // }, {
    //     content: "open the many2one to select another user",
    //     trigger: '.o_form_input_dropdown > input',
    //     run: 'text Demo',
    // }, {
    //     content: "select another user",
    //     trigger: '.ui-autocomplete li:contains(Demo User)',
    //     in_modal: false,
    // }, {
    //     content: "test one2many's line onchange after many2one",
    //     trigger: '.o_form_field:contains([test_trigger] Demo User)',
    //     run: function () {}, // it's a check
    // }, {
    //     content: "test one2many field not triggered onchange",
    //     trigger: 'textarea[name="message_concat"]:propValueContains([test_trigger] Administrator:e)',
    //     in_modal: false,
    //     run: function () {}, // don't change texarea content
    // }, {
    //     content: "save changes",
    //     trigger: '.modal-footer button:contains(Save):contains(Close)'
    // }, {
    //     content: "test one2many triggered the onchange on save for the line",
    //     trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tbody tr td.o_readonly:contains([test_trigger] Demo User))',
    //     run: function () {}, // it's a check
    // }, {
    //     content: "test one2many triggered the onchange on save",
    //     trigger: 'textarea[name="message_concat"]:propValueContains([test_trigger] Demo User:e)',
    //     run: function () {}, // don't change texarea content
    }, { // remove
        content: "remove b",
        trigger: '.tab-pane:eq(0) .o_form_field tbody tr:has(td:containsExact(b)) .o_list_record_delete',
        // trigger: '.tab-pane:eq(0) .o_form_field tbody tr:has(td:containsExact(bbb)) .o_list_record_delete', // FIXME (problem 2)
        extra_trigger: '.tab-pane:eq(0) .o_form_field tbody tr td:containsExact(e)',
        // extra_trigger: '.tab-pane:eq(0) .o_form_field tbody tr td:contains(aaa)', // FIXME (problem 2)
    }, {
        content: "remove e",
        trigger: 'tr:has(td:containsExact(e)) .o_list_record_delete',
        extra_trigger: 'body:not(:has(tr:has(td:containsExact(b))))',
        // extra_trigger: 'body:not(:has(tr:has(td:containsExact(bbb))))', // FIXME (problem 2)
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'body:not(:has(tr:has(td:containsExact(e))))',
    }, { // check saved data
        content: "check data 4",
        trigger: '.o_content:not(:has(.tab-pane:eq(0) .o_form_field tbody tr:has(.o_list_record_delete):eq(4)))',
        run: function () {}, // it's a check
    }, {
        content: "check data 5",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tbody:has(tr td:containsExact(a)):has(tr td:containsExact(c)):has(tr td:containsExact(d)))',
        // trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tbody:has(tr td:containsExact(aaa)):has(tr td:containsExact(c)):has(tr td:containsExact(d)))', // FIXME (problem 2)
        run: function () {}, // it's a check
    }, {
        content: "check data 6",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tbody tr:has(td:containsExact([test_trigger] Administrator)):has(td:containsExact(a)))',
        // trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tbody tr:has(td:containsExact([test_trigger] Administrator)):has(td:containsExact(aaa)))', // FIXME (problem 2)
        run: function () {}, // it's a check
    }, {
        content: "check data 7",
        trigger: '.o_content:has(.tab-pane:eq(2) .o_form_field tbody .o_data_row:eq(2))',
        extra_trigger: '.o_content:not(:has(.tab-pane:eq(2) .o_form_field tbody tr[date-id]:eq(3)))',
        run: function () {}, // it's a check
    }, { // edit
        content: "edit discussion",
        trigger: 'button.o_form_button_edit',
    }, { // add message ddd
        content: "create new message ddd",
        trigger: '.tab-pane:eq(0) .o_form_field_x2many_list_row_add a',
        extra_trigger: '.tab-pane:eq(0) .o_form_field tbody tr:has(td:containsExact(d))',
    }, {
        content: "select another user",
        trigger: '.o_form_field_many2one .o_form_input_dropdown > input',
        extra_trigger: 'body:has(.modal) .tab-pane:eq(0) .o_form_field tbody tr:has(td:containsExact(d))',
        run: 'text Demo',
    }, {
        content: "select demo user",
        trigger: '.ui-autocomplete li a:contains(Demo User)',
        in_modal: false,
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_form_field:contains([] Demo User)',
        // trigger: '.o_form_field:contains([test_trigger] Demo User)', // FIXME (problem 2)
        run: function () {}, // it's a check
    }, {
        content: "insert body",
        trigger: '.o_form_textarea[name="body"] textarea:first',
        run: 'text ddd',
    }, {
        content: "save new message ddd",
        trigger: '.modal-footer button:contains(Save):first',
        extra_trigger: '.o_form_textarea[name="body"] textarea:first:propValue(ddd)',
    }, { // trigger onchange
        content: "blur the one2many",
        trigger: 'input.o_form_required',
        extra_trigger: '.tab-pane:eq(0) .o_form_field tbody:has(tr td:containsExact(ddd))',
    }, { // check onchange data
        content: "check data 8",
        trigger: '.o_form_textarea[name="message_concat"] textarea:propValueContains([test_trigger] Administrator:a\n[test_trigger] Administrator:c\n[test_trigger] Administrator:d\n[test_trigger] Demo User:ddd)',
        // trigger: 'textarea[name="message_concat"]:propValueContains([test_trigger] Administrator:aaa\n[test_trigger] Administrator:c\n[test_trigger] Administrator:d\n[test_trigger] Demo User:ddd)',  // FIXME (problem 2)
        run: function () {}, // don't change texarea content
    }, {
        content: "check data 9",
        trigger: '.o_content:has(.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(3))',
        extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(4)))',
        run: function () {}, // it's a check
    }, { // cancel
        content: "cancel change",
        trigger: '.o_cp_buttons .o_form_button_cancel',
        extra_trigger: '.tab-pane:eq(0) .o_form_field tbody:has(tr td:containsExact(ddd))',
        run: 'click',
    }, {
        content: "confirm cancel change",
        trigger: '.modal-footer button:contains(Ok)',
    },

    /////////////////////////////////////////////////////////////////////////////////////////////
    /////////////////////////////////////////////////////////////////////////////////////////////

    {
        content: "switch to the second form view to test one2many with editable list (toggle menu dropdown)",
        trigger: '.o_sub_menu .oe_secondary_submenu .oe_menu_leaf .oe_menu_text:containsExact(Discussions)',
        extra_trigger: '.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(2)',
        edition: 'community'
    }, {
        content: "switch to the second form view to test one2many with editable list (toggle menu dropdown)",
        trigger: 'nav .o_menu_sections li a:containsExact(Discussions)',
        extra_trigger: '.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(2)',
        edition: 'enterprise'
    }, {
        content: "switch to the second form view to test one2many with editable list (open submenu)",
        trigger: '.o_sub_menu .oe_secondary_submenu .oe_menu_leaf .oe_menu_text:contains(Discussions 2)',
        edition: 'community'
    }, {
        content: "switch to the second form view to test one2many with editable list (open submenu)",
        trigger: 'nav .o_menu_sections ul li a:contains(Discussions 2)',
        edition: 'enterprise'
    }, {
        content: "select previous created record",
        trigger: 'td:contains(test_trigger):last',
        extra_trigger: '.breadcrumb li:containsExact(Discussions 2)',
    }, {
        content: "click on edit",
        trigger: '.o_cp_buttons .o_form_button_edit',
    }, {
        content: "edit content",
        trigger: 'input.o_form_required',
        extra_trigger: ".o_form_editable",
        run: 'text test_trigger2'
    }, {
        content: "click outside to trigger onchange",
        trigger: '.o_form_sheet',
    }, {
        content: "click on a field of the editable list to edit content",
        trigger: '.o_list_view .o_data_row:eq(1) td',
        extra_trigger: '.o_list_view:contains(test_trigger)',
        // extra_trigger: '.o_list_view:contains(test_trigger2)', // FIXME (problem 2)
    }, {
        content: "change text value",
        trigger: '.o_form_textarea[name="body"] textarea:first',
        run: 'text ccc'
    }, {
        content: "click on other field (trigger the line onchange)",
        trigger: '.o_list_view .o_form_field_many2one[name="author"] input',
        run: 'click'
    }, {
    // FIXME (problem 2)
    //     content: "test one2many's line onchange",
    //     trigger: '.o_list_view .o_selected_row td:nth(3):contains(3)',
    //     run: function () {}, // don't blur the many2one
    // }, {
        content: "test one2many field not triggered onchange",
        trigger: '.o_content:not(:has(.o_form_textarea [name="message_concat"] textarea:propValueContains(ccc)))',
        run: function () {}, // don't blur the many2one
    }, {
        content: "open the many2one to select an other user",
        trigger: '.o_list_view .o_form_field_many2one[name="author"] .o_form_input_dropdown > input',
        run: 'text Demo',
    }, {
        content: "select an other user",
        trigger: '.ui-autocomplete li a:contains(Demo User)',
    // FIXME (problem 2)
    // }, {
    //     content: "test one2many's line onchange after many2one",
    //     trigger: '.o_list_editable_form span.o_form_field:contains([test_trigger] Demo User)',
    //     // trigger: '.o_list_editable_form span.o_form_field:contains([test_trigger2] Demo User)',
    //     run: function () {}, // don't blur the many2one
    }, {
        content: "test one2many field not triggered onchange",
        trigger: '.o_content:not(:has(.o_form_textarea[name="message_concat"] textarea:propValueContains(ccc)))',
        run: function () {}, // don't blur the many2one
    }, {
        content: "change text value",
        trigger: '.o_form_textarea[name="body"] textarea:first',
        run: 'text ccccc',
    }, { // check onchange
        content: "click outside to trigger one2many onchange",
        trigger: 'input.o_form_required',
        extra_trigger: 'body:not(:has(.o_form_textarea[name="message_concat"] textarea:first:propValueContains(Demo User)))',
        run: 'click'
    }, {
    // FIXME (problem 2)
    //     content: "test one2many onchange",
    //     trigger: '.o_form_textarea[name="message_concat"] textarea:first:propValueContains([test_trigger2] Demo User:ccccc)',
    //     run: function () {}, // don't change texarea content
    // }, {
        content: "click outside to trigger one2many onchange",
        trigger: '.o_form_field_many2manytags .o_form_input_dropdown > input',
    }, {
        content: "add a tag",
        trigger: '.ui-autocomplete a:first',
    }, { // remove record
        content: "delete the last item in the editable list",
        trigger: '.o_list_view .o_data_row td.o_list_record_delete span:visible:last',
    }, {
        content: "test one2many onchange after delete",
        trigger: '.o_content:not(:has(textarea[name="message_concat"]:propValueContains(Administrator:d)))',
        run: function () {},
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'body:not(:has(tr:has(td:containsExact(d))))',
    }, { // check saved data
    // FIXME (problem 2)
    //     content: "check data 10",
    //     trigger: '.o_form_textarea:containsExact([test_trigger2] Administrator:aaa\n[test_trigger2] Demo User:ccccc)',
    //     trigger: '.o_form_textarea:containsExact([test_trigger2] Administrator:aaa\n[test_trigger2] Demo User:ccccc)',
    //     run: function () {}, // don't change texarea content
    // }, {
        content: "check data 11",
        trigger: '.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(1)',
        extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(2)))',
        run: function () {},
    }, { // edit
        content: "edit discussion",
        trigger: 'button.o_form_button_edit'
    }, { // add message eee
        content: "create new message eee",
        trigger: '.tab-pane:eq(0) .o_form_field_x2many_list_row_add a',
        extra_trigger: 'li.active a[data-toggle="tab"]:contains(Messages)',
    }, {
        content: "change text value",
        trigger: '.o_form_textarea[name="body"] textarea:first',
        run: 'text eee'
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: '.o_form_textarea[name="body"] textarea:first:propValueContains(eee)',
    // FIXME (problem 2) + add an item doesn't work at the end of the tour (problem 3)
    // }, { // check saved data
    //     content: "check data 12",
    //     trigger: '.o_form_textarea[name="body"] textarea:first:containsExact([test_trigger2] Administrator:aaa\n[test_trigger2] Demo User:ccccc\n[test_trigger2] Administrator:eee)',
    //     run: function () {}, // it's a check
    // }, {
    //     content: "check data 13",
    //     trigger: '.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(2)',
    //     extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_form_field tbody .o_data_row:eq(3)))',
    //     run: function () {}, // it's a check
    }]);

// FIXME: apply https://github.com/odoo/odoo/commit/a2479396204d900b267d2446001769bdcbd1f9fa

});
