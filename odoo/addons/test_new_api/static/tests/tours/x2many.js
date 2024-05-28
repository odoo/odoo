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
        run: "click",
    }, { // create test discussion
        content: "create new discussion",
        trigger: 'button.o_list_button_add',
        run: "click",
    }, {
        content: "insert content",
        trigger: '.o_field_widget.o_required_modifier input',
        run: "edit test",
    }, {
        content: "click on moderator many2one dropdown",
        trigger: '.o_field_widget[name=moderator] input',
        run: 'click',
    }, {
        content: "insert value in moderator",
        trigger: '.o_field_widget[name=moderator] input',
        run: "edit test",
    }, {
        content: "click on 'Create and Edit...'",
        trigger: '.o_field_widget[name=moderator] .o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a',
        run: "click",
    }, {
        content: "insert a name into the modal form",
        trigger: '.o_field_widget[name=name] input',
        extra_trigger: '.modal',
        run: `edit user_test_${(inc = new Date().getTime())}`,
    }, {
        content: "insert an email into the modal form",
        trigger: '.o_field_widget[name=login] input',
        run: `edit user_test_${inc}@test`,
    }, {
        content: "save the modal content and create the new moderator",
        trigger: '.o_form_button_save',
        run: "click",
    }, {
        content: "check if the modal is saved",
        trigger: '.o_field_widget[name=moderator] input:value(user_test)',
        isCheck: true,
    }, {
        content: "go to Participants tab to check onchange",
        trigger: '.o_notebook_headers .nav-item a:contains(Participants)',
        run: "click",
    }, {
        content: "check the onchange from the o2m to the m2m",
        trigger: '.o_field_widget[name=participants] .o_data_cell:contains(user_test)',
        isCheck: true,
    }, { // add ourself as participant
        content: "click to add participants",
        trigger: '.o_field_widget[name=participants] .o_field_x2many_list_row_add a',
        run: "click",
    }, {
        content: "select Admin",
        trigger: 'tr:has(td:contains(/^Mitchell Admin$/)) .o_list_record_selector input[type="checkbox"]',
        run: "click",
    }, {
        content: "save selected participants",
        trigger: '.o_select_button',
        extra_trigger: 'tr:has(td:contains(/^Mitchell Admin$/)) .o_list_record_selector input[type="checkbox"]:checked',
        run: "click",
    }, ...stepUtils.saveForm({
        content: "save discussion",
        extra_trigger: '.o_field_widget[name=participants] .o_data_cell:contains(/^Mitchell Admin$/)',
    }), { // add message a
        content: "Select First Tab",
        trigger: '.o_notebook_headers .nav-item a:contains(Messages)',
        run: "click",
    }, {
        content: "create new message a",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        run: "click",
    }, {
        content: "insert body a",
        trigger: '.modal-body textarea:first',
        run: "edit a",
    }, {
        content: "save new message a",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, { // add message b
        content: "create new message b",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_field_widget[name="message_concat"] textarea:value([test] Mitchell Admin:a)',
        run: "click",
    }, {
        content: "insert body b",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit b",
    }, {
        content: "save new message b",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, { // change content to trigger on change
        content: "insert content",
        trigger: '.o_field_widget[name=name] input',
        extra_trigger: '.o_field_widget[name="message_concat"] textarea:value([test] Mitchell Admin:a\n[test] Mitchell Admin:b)',
        run: "edit test_trigger && press Enter",
    }, {
        content: "check onchange",
        trigger: '.o_field_widget[name="message_concat"] textarea:value([test_trigger] Mitchell Admin:a\n[test_trigger] Mitchell Admin:b)',
        isCheck: true,
    }, { // change message b
        content: "edit message b",
        trigger: '.o_field_widget[name=messages] .o_data_cell:contains(/^b$/)',
        // extra_trigger: 'body:not(:has(.tab-pane:eq(0) .o_field_widget tbody .o_data_row:eq(2))) .tab-pane:eq(0) .o_field_widget tbody tr td:contains([test_trigger] )',
        run: "click",
    }, {
        content: "change the body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit bbb",
    }, {
        content: "save changes",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, { // add message c
        content: "create new message c",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_field_widget[name="message_concat"] textarea:value([test_trigger] Mitchell Admin:a\n[test_trigger] Mitchell Admin:bbb)',
        run: "click",
    }, {
        content: "insert body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit c",
    }, {
        content: "save new message c",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, { // add participants
        content: "change tab to Participants",
        trigger: '.o_notebook_headers .nav-item a:contains(Participants)',
        extra_trigger: '.o_field_widget[name=messages] .o_data_row:eq(2)',
        run: "click",
    }, {
        content: "click to add participants",
        trigger: '.o_field_widget[name=participants] .o_field_x2many_list_row_add a',
        run: "click",
    }, {
        content: "select Demo User",
        trigger: 'tr:has(td:contains(/^Marc Demo$/)) .o_list_record_selector input[type="checkbox"]',
        run: "click",
    }, {
        content: "save selected participants",
        trigger: '.o_select_button',
        extra_trigger: 'tr:has(td:contains(/^Marc Demo$/)) .o_list_record_selector input[type="checkbox"]:checked',
        run: "click",
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        run: "click",
    }, {
        content: "go back to tab 1",
        trigger: '.o_notebook_headers .nav-item a:contains(Messages)',
        run: "click",
    }, { // check saved data
        content: "check data 1",
        trigger: '.o_content:has(.o_field_widget[name=messages] tbody .o_data_row:eq(2))',
        extra_trigger: 'body:not(:has(.o_field_widget[name=messages] tbody .o_data_row:eq(3)))',
        isCheck: true,
    }, {
        content: "check data 2",
        trigger: `.o_content:has(.o_field_widget[name=messages] tr:has(td:contains(/^bbb$/)):has(td:contains(/^\\[test_trigger\\] Mitchell Admin$/)))`,
        isCheck: true,
    }, {
        content: "go to tab 3",
        trigger: '.o_notebook_headers .nav-item a:contains(Participants)',
        run: "click",
    }, {
        content: "check data 3",
        trigger: '.o_content:has(.o_field_widget[name=participants] tbody .o_data_row:eq(2))',
        extra_trigger: 'body:not(:has(.o_field_widget[name=participants] tbody .o_data_row:eq(3)))',
        isCheck: true,
    }, {
        content: "change tab to Messages",
        trigger: '.o_notebook_headers .nav-item a:contains(Messages)',
        extra_trigger: '.o_form_editable',
        run: "click",
    }, { // add message d
        content: "create new message d",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_notebook_headers .nav-link.active:contains(Messages)',
        run: "click",
    }, {
        content: "insert body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit d",
    }, {
        content: "save new message d",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, { // add message e
        content: "create new message e",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_field_widget[name=messages] .o_data_cell:contains(/^d$/)',
        run: "click",
    }, {
        content: "insert body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit e",
    }, {
        content: "save new message e",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, { // change message a
        content: "edit message a",
        trigger: '.o_field_widget[name=messages] .o_data_cell:contains(/^a$/)',
        extra_trigger: '.o_field_widget[name=messages] .o_data_cell:contains(/^e$/)',
        run: "click",
    }, {
        content: "change the body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit aaa",
    }, {
        content: "save changes",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, { // change message e
        content: "edit message e",
        trigger: '.o_field_widget[name=messages] .o_data_cell:contains(/^e$/)',
        extra_trigger: '.o_field_widget[name=messages] .o_data_cell:contains(/^aaa$/)',
        run: "click",
    }, {
        content: "open the many2one to select another user",
        trigger: '.o_field_widget[name="author"] input',
        run: "edit Marc",
    }, {
        content: "select another user",
        trigger: '.o_field_widget[name="author"] .o-autocomplete--dropdown-menu li:contains(Marc Demo)',
        run: "click",
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_field_widget[name=name]:contains([test_trigger] Marc Demo)',
        isCheck: true,
    }, {
        content: "test one2many field not triggered onchange",
        trigger: '.o_field_widget[name="message_concat"] textarea:value([test_trigger] Mitchell Admin:e)',
        in_modal: false,
        isCheck: true, // don't change texarea content
    }, {
        content: "save changes",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, {
        content: "test one2many triggered the onchange on save for the line",
        trigger: '.o_field_widget[name=messages] .o_data_cell:contains([test_trigger] Marc Demo)',
        isCheck: true,
    }, {
        content: "test one2many triggered the onchange on save",
        trigger: '.o_field_widget[name="message_concat"] textarea:value([test_trigger] Marc Demo:e)',
        isCheck: true, // don't change texarea content
    }, { // remove
        content: "remove b",
        trigger: '.o_field_widget[name=messages] .o_data_row:has(.o_data_cell:contains(/^bbb$/)) .o_list_record_remove',
        run: "click",
    }, {
        content: "remove e",
        trigger: '.o_field_widget[name=messages] .o_data_row:has(.o_data_cell:contains(/^e$/)) .o_list_record_remove',
        run: "click",
    }, { // save
        content: "save discussion",
        trigger: 'button.o_form_button_save',
        extra_trigger: 'body:not(:has(tr:has(td:contains(/^e$/))))',
        run: "click",
    }, { // check saved data
        content: "check data 4",
        trigger: '.o_content:not(:has(.o_field_widget[name=messages] tbody tr:has(.o_list_record_remove):eq(4)))',
        isCheck: true,
    }, {
        content: "check data 5",
        trigger: '.o_content:has(.o_field_widget[name=messages] tbody:has(tr td:contains(/^aaa$/)):has(tr td:contains(/^c$/)):has(tr td:contains(/^d$/)))',
        isCheck: true,
    }, {
        content: "check data 6",
        trigger: `.o_content:has(.o_field_widget[name=messages] tbody tr:has(td:contains(/^\\[test_trigger\\] Mitchell Admin$/)):has(td:contains(/^aaa$/)))`,
        isCheck: true,
    }, {
        content: "go to Participants",
        trigger: '.o_notebook_headers .nav-item a:contains(Participants)',
        run: "click",
    }, {
        content: "check data 7",
        trigger: '.o_content:has(.o_field_widget[name=participants] tbody .o_data_row:eq(2))',
        extra_trigger: '.o_content:not(:has(.o_field_widget[name=participants] tbody .o_data_row:eq(3)))',
        isCheck: true,
    }, {
        content: "go to Messages",
        trigger: '.o_notebook_headers .nav-item a:contains(Messages)',
        run: "click",
    }, { // add message ddd
        content: "create new message ddd",
        trigger: '.o_field_widget[name=messages] .o_field_x2many_list_row_add a',
        extra_trigger: '.o_form_editable .o_field_widget[name=messages] tbody tr:has(td:contains(/^d$/))',
        run: "click",
    }, {
        content: "select another user",
        trigger: '.o_field_widget[name=author] input',
        run: "edit Marc",
    }, {
        content: "select demo user",
        trigger: '.o_field_widget[name="author"] .o-autocomplete--dropdown-menu li:contains(Marc Demo)',
        run: "click",
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_field_widget[name=name]:contains([test_trigger] Marc Demo)',
        isCheck: true,
    }, {
        content: "insert body",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit ddd",
    }, {
        content: "save new message ddd",
        trigger: '.modal-footer .o_form_button_save',
        run: "click",
    }, { // check onchange data
        content: "check data 8",
        trigger: '.o_field_widget[name="message_concat"] textarea:value([test_trigger] Mitchell Admin:aaa\n[test_trigger] Mitchell Admin:c\n[test_trigger] Mitchell Admin:d\n[test_trigger] Marc Demo:ddd)',
        isCheck: true, // don't change texarea content
    }, {
        content: "check data 9",
        trigger: '.o_content:has(.o_field_widget[name=messages] .o_data_row:eq(3))',
        extra_trigger: 'body:not(:has(.o_field_widget[name=messages] .o_data_row:eq(4)))',
        isCheck: true,
    }, ...stepUtils.discardForm({ // cancel
        content: "cancel change",
        extra_trigger: '.o_field_widget[name=messages]:has(tr td:contains(/^ddd$/))',
    }),

    /////////////////////////////////////////////////////////////////////////////////////////////
    // Discussions 2
    /////////////////////////////////////////////////////////////////////////////////////////////

    {
        content: "switch to the second form view to test one2many with editable list (toggle menu dropdown)",
        trigger: 'button[data-menu-xmlid="test_new_api.menu_main"], li.o_extra_menu_items a i.fa-plus',
        run: "click",
    }, {
        content: "switch to the second form view to test one2many with editable list (open submenu)",
        trigger: '.dropdown-item[data-menu-xmlid="test_new_api.menu_discussions_2"]',
        run: "click",
    }, {
        content: "select previous created record",
        trigger: 'td:contains(test_trigger):last',
        extra_trigger: '.o_breadcrumb:contains(Discussions 2)',
        run: "click",
    }, {
        content: "edit content",
        trigger: '.o_field_widget[name=name] input',
        extra_trigger: ".o_form_editable",
        run: "edit test_trigger2 && click body",
    }, {
        content: "click outside to trigger onchange",
        trigger: '.o_form_sheet',
        run: "click",
    }, {
        content: "click on a field of the editable list to edit content",
        trigger: '.o_field_widget[name=messages] .o_data_row:eq(1) td',
        extra_trigger: '.o_field_widget[name=messages]:contains(test_trigger2)',
        run: "click",
    }, {
        content: "change text value",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit ccc && click .o_selected_row",
    }, {
        content: "click on other field (trigger the line onchange)",
        trigger: '.o_field_widget[name=messages] .o_field_many2one[name="author"] input',
        run: 'click'
    }, {
        content: "test one2many's line onchange",
        trigger: '.o_field_widget[name=messages] .o_selected_row td:eq(3):contains(3)',
        isCheck: true, // don't blur the many2one
    }, {
        content: "open the many2one to select an other user",
        trigger: '.o_field_widget[name=messages] .o_field_many2one[name="author"] input',
        run: "edit Marc",
    }, {
        content: "select an other user",
        trigger: '.o_field_widget[name="author"] .o-autocomplete--dropdown-menu li:contains(Marc Demo)',
        run: "click",
    }, {
        content: "test one2many's line onchange after many2one",
        trigger: '.o_field_widget[name=messages] td:contains([test_trigger2] Marc Demo)',
        isCheck: true, // don't blur the many2one
    }, {
        content: "change text value",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit ccccc",
    }, { // check onchange
        content: "click outside to trigger one2many onchange",
        trigger: '.o_field_widget[name=name] input',
        run: 'click'
    }, {
        content: "test one2many onchange",
        trigger: '.o_field_widget[name="message_concat"] textarea:value([test_trigger2] Marc Demo:ccccc)',
        isCheck: true, // don't change texarea content
    }, {
        content: "click outside to trigger one2many onchange",
        trigger: '.o_field_widget[name=categories] input',
        run: "edit Test",
    }, {
        content: "add a tag",
        trigger: '.o_field_widget[name="categories"] .o-autocomplete--dropdown-menu li a:first',
        run: "click",
    }, { // remove record
        content: "delete the last item in the editable list",
        trigger: '.o_field_widget[name=messages] .o_data_row td.o_list_record_remove button:visible:last',
        run: "click",
    }, {
        content: "test one2many onchange after delete",
        trigger: '.o_content:not(:has(.o_field_widget[name="message_concat"] textarea:value(Mitchell Admin:d)))',
        isCheck: true,
    }, ...stepUtils.saveForm({ // save
        content: "save discussion",
        extra_trigger: 'body:not(:has(tr:has(td:contains(/^d$/))))',
    }), { // check saved data
        content: "check data 10",
        trigger: '.o_field_widget[name=message_concat] textarea:value([test_trigger2] Mitchell Admin:aaa\n[test_trigger2] Marc Demo:ccccc)',
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
        run: "click",
    }, {
        content: "change text value",
        trigger: '.o_field_widget[name="body"] textarea',
        run: "edit eee",
    }, ...stepUtils.saveForm({ // save
        content: "save discussion",
        extra_trigger: '.o_field_widget[name="body"] textarea:value(eee)',
    }), { // check saved data
        content: "check data 12",
        trigger: '.o_field_widget[name="message_concat"] textarea:value([test_trigger2] Mitchell Admin:aaa\n[test_trigger2] Marc Demo:ccccc\n[test_trigger2] Mitchell Admin:eee)',
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
        run: "click",
    }, {
        content: "switch to the thied form view to test onchange changing one2many (open submenu)",
        trigger: '.dropdown-item[data-menu-xmlid="test_new_api.menu_discussions_3"]',
        run: "click",
    }, {
        content: "wait web client",
        trigger: '.o_breadcrumb:contains(Discussions 3)',
        run: "click",
    }, {
        content: "create new discussion",
        trigger: 'button.o_list_button_add',
        run: "click",
    }, {
        content: "set discussion title to generate dummy message",
        trigger: '.o_field_widget[name=name] input',
        run:     "edit {generate_dummy_message} && click body",
    }, {
        content: "check new dummy message happened",
        trigger: '.o_field_widget[name=messages] .o_data_row .o_list_number:contains(/^13$/)',
        extra_trigger: '.o_field_widget[name=important_messages] .o_data_row .o_list_number:contains(/^13$/)',
        isCheck: true,
    }, {
        content: "check field not in embedded view received correctly",
        trigger: '.o_field_widget[name=messages] .o_data_row input[type="checkbox"]:checked',
        isCheck: true,
    }, {
        content: "empty discussion title",
        trigger: '.o_field_widget[name=name] input',
        run:     "edit removed_title && click body",
    }, {
        content: "onchange happened",
        trigger: '.o_field_widget[name=messages] .o_data_row td:contains([removed_title])',
        isCheck: true,
    }, {
        content: "set discussion title to generate dummy message",
        trigger: '.o_field_widget[name=name] input',
        run:     "edit {generate_dummy_message} && click body",
    }, {
        content: "check update and new dummy message happened",
        trigger: '.o_field_widget[name=messages] .o_data_row .o_list_number:contains(/^22$/)',
        extra_trigger: '.o_field_widget[name=important_messages] .o_data_row .o_list_number:contains(/^22$/)',
        isCheck: true,
    },
    ...stepUtils.discardForm(),
    ]});
