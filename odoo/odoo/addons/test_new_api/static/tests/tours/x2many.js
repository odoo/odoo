/** @odoo-module **/

    import { stepUtils } from "@web_tour/tour_service/tour_utils";
    import { registry } from "@web/core/registry";
    var inc;

    registry.category("web_tour.tours").add('widget_x2many', {
        url: '/web?debug=tests#action=test_new_api.action_discussions',
        test: true,
        steps: () => [
    /////////////////////////////////////////////////////////////////////////////////////////////
    // Discussions
    /////////////////////////////////////////////////////////////////////////////////////////////
    {
        content: "wait web client",
        trigger: '.o_breadcrumb:contains(Discussions)',
    }, { // create test discussion
        content: "create new discussion",
        trigger: 'button.o_list_button_add',
    }, {
        content: "insert content",
        trigger: '.o_field_widget.o_required_modifier input',
        run: 'text test',
    }, {
        content: "click on moderator many2one dropdown",
        trigger: '.o_field_widget[name=moderator] input',
        run: 'click',
    }, {
        content: "insert value in moderator",
        trigger: '.o_field_widget[name=moderator] input',
        run: 'text test',
    }, {
        content: "click on 'Create and Edit...'",
        trigger: '.o_field_widget[name=moderator] .o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a',
    }, {
        content: "insert a name into the modal form",
        trigger: '.o_field_widget[name=name] input',
        extra_trigger: '.modal',
        run: function (action_helper) {
            action_helper.text('user_test_' + (inc = new Date().getTime()));
        }
    }, {
        content: "insert an email into the modal form",
        trigger: '.o_field_widget[name=login] input',
        run: function (action_helper) {
            action_helper.text('user_test_' + inc + '@test');
        }
    }, {
        content: "save the modal content and create the new moderator",
        trigger: '.o_form_button_save',
    }, {
        content: "check if the modal is saved",
        trigger: '.o_field_widget[name=moderator] input:propValueContains(user_test)',
        isCheck: true,
    }, {
        content: "go to Participants tab to check onchange",
        trigger: '.o_notebook_headers .nav-item a:contains(Participants)',
    }, {
        content: "check the onchange from the o2m to the m2m",
        trigger: '.o_field_widget[name=participants] .o_data_cell:contains(user_test)',
        isCheck: true,
    }, { // add ourself as participant
        content: "click to add participants",
        trigger: '.o_field_widget[name=participants] .o_field_x2many_list_row_add a'
    }, {
        content: "select Admin",
        trigger: 'tr:has(td:containsExact(Mitchell Admin)) .o_list_record_selector input[type="checkbox"]'
    }, {
        content: "save selected participants",
        trigger: '.o_select_button',
        extra_trigger: 'tr:has(td:containsExact(Mitchell Admin)) .o_list_record_selector input[type="checkbox"]:propChecked',
    }, ...stepUtils.saveForm({
        content: "save discussion",
        extra_trigger: '.o_field_widget[name=participants] .o_data_cell:containsExact(Mitchell Admin)',
    }), { // add message a
        content: "Select First Tab",
        trigger: '.o_notebook_headers .nav-item a:contains(Messages)',
    }, {
        content: "create new message a",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a'
    }, {
        content: "insert body a",
        trigger: '.modal-body textarea:first',
        run: 'text a',
    }, {
        content: "save new message a",
        trigger: '.modal-footer .o_form_button_save',
    }, { // add message b
        content: "create new message b",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_field_widget[name="message_concat"] textarea:propValue([test] Mitchell Admin:a)',
    }, {
        content: "insert body b",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text b',
    }, {
        content: "save new message b",
        trigger: '.modal-footer .o_form_button_save',
    }, { // change content to trigger on change
        content: "insert content",
        trigger: '.o_field_widget[name=name] input',
        extra_trigger: '.o_field_widget[name="message_concat"] textarea:propValue([test] Mitchell Admin:a\n[test] Mitchell Admin:b)',
        run: 'text test_trigger',
    }, {
        content: "check onchange",
        trigger: '.o_field_widget[name="message_concat"] textarea:propValue([test_trigger] Mitchell Admin:a\n[test_trigger] Mitchell Admin:b)',
        isCheck: true,
    }, { // change message b
        content: "edit message b",
        trigger: '.o_field_widget[name=messages] .o_data_cell:containsExact(b)',
        // extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2))) .tab-pane:eq(0) .o_field_widget tbody tr td:contains([test_trigger] )',
    }, {
        content: "change the body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text bbb',
    }, {
        content: "save changes",
        trigger: '.modal-footer .o_form_button_save',
    }, { // add message c
        content: "create new message c",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_field_widget[name="message_concat"] textarea:propValue([test_trigger] Mitchell Admin:a\n[test_trigger] Mitchell Admin:bbb)',
    }, {
        content: "insert body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text c',
    }, {
        content: "save new message c",
        trigger: '.modal-footer .o_form_button_save',
    }, { // add participants
        content: "change tab to Participants",
        trigger: '.o_notebook_headers .nav-item a:contains(Participants)',
        extra_trigger: '.o_field_widget[name=messages] .o_data_row:eq(2)',
    }, {
        content: "click to add participants",
        trigger: '.o_field_widget[name=participants] .o_field_x2many_list_row_add a',
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
    }, {
        content: "go back to tab 1",
        trigger: '.o_notebook_headers .nav-item a:contains(Messages)',
    }, { // check saved data
        content: "check data 1",
        trigger: '.o_content:has(.o_field_widget[name=messages] tbody .o_data_row:eq(2))',
        extra_trigger: 'body:not(:has(.o_field_widget[name=messages] tbody .o_data_row:eq(3)))',
        isCheck: true,
    }, {
        content: "check data 2",
        trigger: '.o_content:has(.o_field_widget[name=messages] tr:has(td:containsExact(bbb)):has(td:containsExact([test_trigger] Mitchell Admin)))',
        isCheck: true,
    }, {
        content: "go to tab 3",
        trigger: '.o_notebook_headers .nav-item a:contains(Participants)',
    }, {
        content: "check data 3",
        trigger: '.o_content:has(.o_field_widget[name=participants] tbody .o_data_row:eq(2))',
        extra_trigger: 'body:not(:has(.o_field_widget[name=participants] tbody .o_data_row:eq(3)))',
        isCheck: true,
    }, {
        content: "change tab to Messages",
        trigger: '.o_notebook_headers .nav-item a:contains(Messages)',
        extra_trigger: '.o_form_editable',
    }, { // add message d
        content: "create new message d",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_notebook_headers .nav-link.active:contains(Messages)',
    }, {
        content: "insert body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text d',
    }, {
        content: "save new message d",
        trigger: '.modal-footer .o_form_button_save',
    }, { // add message e
        content: "create new message e",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_field_widget[name=messages] .o_data_cell:containsExact(d)',
    }, {
        content: "insert body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text e',
    }, {
        content: "save new message e",
        trigger: '.modal-footer .o_form_button_save',
    }, { // change message a
        content: "edit message a",
        trigger: '.o_field_widget[name=messages] .o_data_cell:containsExact(a)',
        extra_trigger: '.o_field_widget[name=messages] .o_data_cell:containsExact(e)',
    }, {
        content: "change the body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text aaa',
    }, {
        content: "save changes",
        trigger: '.modal-footer .o_form_button_save',
    }, { // change message e
        content: "edit message e",
        trigger: '.o_field_widget[name=messages] .o_data_cell:containsExact(e)',
        extra_trigger: '.o_field_widget[name=messages] .o_data_cell:containsExact(aaa)',
    }, {
        content: "open the many2one to select another user",
        trigger: '.o_field_widget[name="author"] input',
        run: 'text Marc',
    }, {
        content: "select another user",
        trigger: '.o_field_widget[name="author"] .o-autocomplete--dropdown-menu li:contains(Marc Demo)',
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_field_widget[name=name]:contains([test_trigger] Marc Demo)',
        isCheck: true,
    }, {
        content: "test one2many field not triggered onchange",
        trigger: '.o_field_widget[name="message_concat"] textarea:propValueContains([test_trigger] Mitchell Admin:e)',
        in_modal: false,
        isCheck: true, // don't change texarea content
    }, {
        content: "save changes",
        trigger: '.modal-footer .o_form_button_save'
    }, {
        content: "test one2many triggered the onchange on save for the line",
        trigger: '.o_field_widget[name=messages] .o_data_cell:contains([test_trigger] Marc Demo)',
        isCheck: true,
    }, {
        content: "test one2many triggered the onchange on save",
        trigger: '.o_field_widget[name="message_concat"] textarea:propValueContains([test_trigger] Marc Demo:e)',
        isCheck: true, // don't change texarea content
    }, { // remove
        content: "remove b",
        trigger: '.o_field_widget[name=messages] .o_data_row:has(.o_data_cell:containsExact(bbb)) .o_list_record_remove',
    }, {
        content: "remove e",
        trigger: '.o_field_widget[name=messages] .o_data_row:has(.o_data_cell:containsExact(e)) .o_list_record_remove',
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'body:not(:has(tr:has(td:containsExact(e))))',
    }, { // check saved data
        content: "check data 4",
        trigger: '.o_content:not(:has(.o_field_widget[name=messages] tbody tr:has(.o_list_record_remove):eq(4)))',
        isCheck: true,
    }, {
        content: "check data 5",
        trigger: '.o_content:has(.o_field_widget[name=messages] tbody:has(tr td:containsExact(aaa)):has(tr td:containsExact(c)):has(tr td:containsExact(d)))',
        isCheck: true,
    }, {
        content: "check data 6",
        trigger: '.o_content:has(.o_field_widget[name=messages] tbody tr:has(td:containsExact([test_trigger] Mitchell Admin)):has(td:containsExact(aaa)))',
        isCheck: true,
    }, {
        content: "go to Participants",
        trigger: '.o_notebook_headers .nav-item a:contains(Participants)',
    }, {
        content: "check data 7",
        trigger: '.o_content:has(.o_field_widget[name=participants] tbody .o_data_row:eq(2))',
        extra_trigger: '.o_content:not(:has(.o_field_widget[name=participants] tbody .o_data_row:eq(3)))',
        isCheck: true,
    }, {
        content: "go to Messages",
        trigger: '.o_notebook_headers .nav-item a:contains(Messages)',
    }, { // add message ddd
        content: "create new message ddd",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_form_editable .o_field_widget[name=messages] tbody tr:has(td:containsExact(d))',
    }, {
        content: "select another user",
        trigger: '.o_field_widget[name=author] input',
        run: 'text Marc',
    }, {
        content: "select demo user",
        trigger: '.o_field_widget[name="author"] .o-autocomplete--dropdown-menu li:contains(Marc Demo)',
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_field_widget[name=name]:contains([test_trigger] Marc Demo)',
        isCheck: true,
    }, {
        content: "insert body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text ddd',
    }, {
        content: "save new message ddd",
        trigger: '.modal-footer .o_form_button_save',
    }, { // check onchange data
        content: "check data 8",
        trigger: '.o_field_widget[name="message_concat"] textarea:propValueContains([test_trigger] Mitchell Admin:aaa\n[test_trigger] Mitchell Admin:c\n[test_trigger] Mitchell Admin:d\n[test_trigger] Marc Demo:ddd)',
        isCheck: true, // don't change texarea content
    }, {
        content: "check data 9",
        trigger: '.o_content:has(.o_field_widget[name=messages] .o_data_row:eq(3))',
        extra_trigger: 'body:not(:has(.o_field_widget[name=messages] .o_data_row:eq(4)))',
        isCheck: true,
    }, ...stepUtils.discardForm({ // cancel
        content: "cancel change",
        extra_trigger: '.o_field_widget[name=messages]:has(tr td:containsExact(ddd))',
    }),

    /////////////////////////////////////////////////////////////////////////////////////////////
    // Discussions 2
    /////////////////////////////////////////////////////////////////////////////////////////////

    {
        content: "switch to the second form view to test one2many with editable list (toggle menu dropdown)",
        trigger: 'button[data-menu-xmlid="test_new_api.menu_main"], li.o_extra_menu_items a i.fa-plus',
    }, {
        content: "switch to the second form view to test one2many with editable list (open submenu)",
        trigger: '.dropdown-item[data-menu-xmlid="test_new_api.menu_discussions_2"]',
    }, {
        content: "select previous created record",
        trigger: 'td:contains(test_trigger):last',
        extra_trigger: '.o_breadcrumb:contains(Discussions 2)',
    }, {
        content: "edit content",
        trigger: '.o_field_widget[name=name] input',
        extra_trigger: ".o_form_editable",
        run: 'text test_trigger2'
    }, {
        content: "click outside to trigger onchange",
        trigger: '.o_form_sheet',
    }, {
        content: "click on a field of the editable list to edit content",
        trigger: '.o_field_widget[name=messages] .o_data_row:eq(1) td',
        extra_trigger: '.o_field_widget[name=messages]:contains(test_trigger2)',
    }, {
        content: "change text value",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text ccc'
    }, {
        content: "click on other field (trigger the line onchange)",
        trigger: '.o_field_widget[name=messages] .o_field_many2one[name="author"] input',
        run: 'click'
    }, {
        content: "test one2many's line onchange",
        trigger: '.o_field_widget[name=messages] .o_selected_row td:nth(3):contains(3)',
        isCheck: true, // don't blur the many2one
    }, {
        content: "open the many2one to select an other user",
        trigger: '.o_field_widget[name=messages] .o_field_many2one[name="author"] input',
        run: 'text Marc',
    }, {
        content: "select an other user",
        trigger: '.o_field_widget[name="author"] .o-autocomplete--dropdown-menu li:contains(Marc Demo)',
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_field_widget[name=messages] td:contains([test_trigger2] Marc Demo)',
        isCheck: true, // don't blur the many2one
    }, {
        content: "change text value",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text ccccc',
    }, { // check onchange
        content: "click outside to trigger one2many onchange",
        trigger: '.o_field_widget[name=name] input',
        run: 'click'
    }, {
        content: "test one2many onchange",
        trigger: '.o_field_widget[name="message_concat"] textarea:propValueContains([test_trigger2] Marc Demo:ccccc)',
        isCheck: true, // don't change texarea content
    }, {
        content: "click outside to trigger one2many onchange",
        trigger: '.o_field_widget[name=categories] input',
    }, {
        content: "add a tag",
        trigger: '.o_field_widget[name="categories"] .o-autocomplete--dropdown-menu li a:first',
    }, { // remove record
        content: "delete the last item in the editable list",
        trigger: '.o_field_widget[name=messages] .o_data_row td.o_list_record_remove button:visible:last',
    }, {
        content: "test one2many onchange after delete",
        trigger: '.o_content:not(:has(.o_field_widget[name="message_concat"] textarea:propValueContains(Mitchell Admin:d)))',
        isCheck: true,
    }, ...stepUtils.saveForm({ // save
        content: "save discussion",
        extra_trigger: 'body:not(:has(tr:has(td:containsExact(d))))',
    }), { // check saved data
        content: "check data 10",
        trigger: '.o_field_widget[name=message_concat] textarea:propValueContains([test_trigger2] Mitchell Admin:aaa\n[test_trigger2] Marc Demo:ccccc)',
        isCheck: true, // don't change texarea content
    }, {
        content: "check data 11",
        trigger: '.o_field_widget[name=messages] tbody .o_data_row:eq(1)',
        extra_trigger: 'body:not(:has(.o_field_widget[name=messages] tbody .o_data_row:eq(2)))',
        isCheck: true,
    }, { // add message eee
        content: "create new message eee",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_form_editable .nav-link.active:contains(Messages)',
    }, {
        content: "change text value",
        trigger: '.o_field_widget[name="body"] textarea',
        run: 'text eee'
    }, ...stepUtils.saveForm({ // save
        content: "save discussion",
        extra_trigger: '.o_field_widget[name="body"] textarea:propValueContains(eee)',
    }), { // check saved data
        content: "check data 12",
        trigger: '.o_field_widget[name="message_concat"] textarea:propValueContains([test_trigger2] Mitchell Admin:aaa\n[test_trigger2] Marc Demo:ccccc\n[test_trigger2] Mitchell Admin:eee)',
        isCheck: true,
    }, {
        content: "check data 13",
        trigger: '.o_field_widget[name=messages] .o_data_row:eq(2)',
        extra_trigger: 'body:not(:has(.o_field_widget[name=messages] .o_data_row:eq(3)))',
        isCheck: true,
    },

    /////////////////////////////////////////////////////////////////////////////////////////////
    // Discussions 3
    /////////////////////////////////////////////////////////////////////////////////////////////

    {
        content: "switch to the third form view to test onchange changing one2many (toggle menu dropdown)",
        trigger: 'button[data-menu-xmlid="test_new_api.menu_main"], li.o_extra_menu_items a i.fa-plus',
        extra_trigger: '.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2)',
    }, {
        content: "switch to the thied form view to test onchange changing one2many (open submenu)",
        trigger: '.dropdown-item[data-menu-xmlid="test_new_api.menu_discussions_3"]',
    }, {
        content: "wait web client",
        trigger: '.o_breadcrumb:contains(Discussions 3)',
    }, {
        content: "create new discussion",
        trigger: 'button.o_list_button_add',
    }, {
        content: "set discussion title to generate dummy message",
        trigger: '.o_field_widget[name=name] input',
        run:     'text {generate_dummy_message}',
    }, {
        content: "check new dummy message happened",
        trigger: '.o_field_widget[name=messages] .o_data_row .o_list_number:containsExact(13)',
        extra_trigger: '.o_field_widget[name=important_messages] .o_data_row .o_list_number:containsExact(13)',
        isCheck: true,
    }, {
        content: "check field not in embedded view received correctly",
        trigger: '.o_field_widget[name=messages] .o_data_row input[type="checkbox"]:propChecked',
        isCheck: true,
    }, {
        content: "empty discussion title",
        trigger: '.o_field_widget[name=name] input',
        run:     'text removed_title',
    }, {
        content: "onchange happened",
        trigger: '.o_field_widget[name=messages] .o_data_row td:contains([removed_title])',
        isCheck: true,
    }, {
        content: "set discussion title to generate dummy message",
        trigger: '.o_field_widget[name=name] input',
        run:     'text {generate_dummy_message}',
    }, {
        content: "check update and new dummy message happened",
        trigger: '.o_field_widget[name=messages] .o_data_row .o_list_number:containsExact(22)',
        extra_trigger: '.o_field_widget[name=important_messages] .o_data_row .o_list_number:containsExact(22)',
        isCheck: true,
    },
    ...stepUtils.discardForm(),
    ]});
