odoo.define('web_tests.tour', function (require) {
'use strict';

var Tour = require('web.Tour');

Tour.register({
    id:   'widget_x2many',
    name: "one2many and many2many checks",
    mode: 'test',

    steps: [
        {
            title:      "wait web client",
            waitFor:    '.oe-view-title:contains(Discussions)'
        },
        // create test discussion
        
        {
            title:      "create new discussion",
            element:    '.oe_application:has(.oe-view-title:contains(Discussions)) button.oe_list_add'
        },
        {
            title:      "insert title",
            element:    '.oe_form_required input',
            sampleText: 'test'
        },

        // add message a

        {
            title:      "create new message a",
            waitFor:    '.oe_form_required input:propValue(test)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body a",
            element:    '.modal textarea.field_text',
            sampleText: 'a'
        },
        {
            title:      "save new message a",
            waitFor:    '.modal textarea.field_text:propValue(a)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // add message b
        
        {
            title:      "create new message b",
            waitNot:    '.modal',
            waitFor:    '.oe_application:has(.oe_list_field_cell):has(textarea[name="message_concat"]:propValue([test] Administrator:a))',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body b",
            element:    '.modal textarea.field_text',
            sampleText: 'b'
        },
        {
            title:      "save new message b",
            waitFor:    '.modal textarea.field_text:propValue(b)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // change title to trigger on change

        {
            title:      "insert title",
            waitNot:    '.modal',
            waitFor:    'textarea[name="message_concat"]:propValue([test] Administrator:a\n[test] Administrator:b)',
            element:    '.oe_form_required input',
            sampleText: 'test_trigger'
        },
        {
            title:      "blur the title field",
            waitFor:    '.oe_form_required input:propValue(test_trigger)',
            element:    '.oe_form_field_many2one input:first',
        },
        {
            title:      "check onchange",
            waitFor:    'textarea[name="message_concat"]:propValue([test_trigger] Administrator:a\n[test_trigger] Administrator:b)',
        },

        // change message b
        
        {
            title:      "edit message b",
            waitFor:    'tr:has(.oe_list_field_cell):not(:has(.oe_list_record_selector)):eq(1) .oe_list_field_cell:contains([test_trigger] )',
            waitNot:    'tr:has(.oe_list_field_cell):not(:has(.oe_list_record_selector)):eq(2)',
            element:    '.oe_list_field_cell:containsExact(b)'
        },
        {
            title:      "change the body",
            element:    '.modal textarea.field_text',
            sampleText: 'bbb'
        },
        {
            title:      "save changes",
            waitFor:    '.modal textarea.field_text:propValue(bbb)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // add message c
        
        {
            title:      "create new message c",
            waitNot:    '.modal',
            waitFor:    'textarea[name="message_concat"]:propValue([test_trigger] Administrator:a\n[test_trigger] Administrator:bbb)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body",
            element:    '.modal textarea.field_text',
            sampleText: 'c'
        },
        {
            title:      "save new message c",
            waitFor:    '.modal textarea.field_text:propValue(c)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // add participants

        {
            title:      "change tab to Participants",
            waitNot:    '.modal',
            waitFor:    '.oe_form_field_one2many .oe_list_field_cell:eq(3)',
            element:    '[data-toggle="tab"]:contains(Participants)'
        },
        {
            title:      "click to add participants",
            element:    '.tab-pane:eq(1).active .oe_form_field_many2many_list_row_add a'
        },
        {
            title:      "select participant 1",
            element:    '.modal .oe_list_record_selector input[type="checkbox"]:eq(0)'
        },
        {
            title:      "select participant 2",
            waitFor:    '.modal .oe_list_record_selector input[type="checkbox"]:eq(0):propChecked',
            element:    '.modal .oe_list_record_selector input[type="checkbox"]:eq(1)'
        },
        {
            title:      "save selected participants",
            waitFor:    '.modal .oe_list_record_selector input[type="checkbox"]:eq(1):propChecked',
            element:    '.oe_selectcreatepopup-search-select'
        },

        // save
        
        {
            title:      "save discussion",
            waitFor:    '.oe_form_field_many2many tbody tr:has(.oe_list_field_char):eq(1)',
            waitNot:    '.oe_form_field_many2many tbody tr:has(.oe_list_field_char):eq(2)',
            element:    'button.oe_form_button_save'
        },

        // check saved data

        {
            title:      "check data 1",
            waitFor:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_char):eq(2)',
            waitNot:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_char):eq(3)',
        },
        {
            title:      "check data 2",
            waitFor:    '.oe_form_field_one2many tr:has(.oe_list_field_text:containsExact(bbb)):has(.oe_list_field_char:containsExact([test_trigger] Administrator))',
        },
        {
            title:      "check data 3",
            waitFor:    '.oe_form_field_many2many tbody tr:has(.oe_list_field_char):eq(1)',
            waitNot:    '.oe_form_field_many2many tbody tr:has(.oe_list_field_char):eq(2)',
        },

        // edit

        {
            title:      "edit discussion",
            element:    'button.oe_form_button_edit'
        },
        {
            title:      "change tab to Participants",
            waitFor:    '.oe_form_editable',
            element:    '[data-toggle="tab"]:contains(Messages)'
        },

        // add message d

        {
            title:      "create new message d",
            waitFor:    'li.active a[data-toggle="tab"]:contains(Messages)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body",
            element:    '.modal textarea.field_text',
            sampleText: 'd'
        },
        {
            title:      "save new message d",
            waitFor:    '.modal textarea.field_text:propValue(d)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // add message e
        
        {
            title:      "create new message e",
            waitNot:    '.modal',
            waitFor:    '.oe_list_field_cell:containsExact(d)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body",
            element:    '.modal textarea.field_text',
            sampleText: 'e'
        },
        {
            title:      "save new message e",
            waitFor:    '.modal textarea.field_text:propValue(e)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // change message a

        {
            title:      "create new message aaa",
            waitNot:    '.modal',
            waitFor:    '.oe_list_field_cell:containsExact(e)',
            element:    '.oe_list_field_cell:containsExact(a)'
        },
        {
            title:      "change the body",
            element:    '.modal textarea.field_text',
            sampleText: 'aaa'
        },
        {
            title:      "save changes",
            waitFor:    '.modal textarea.field_text:propValue(aaa)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // remove
        
        {
            title:      "remove b",
            waitNot:    '.modal',
            waitFor:    '.oe_list_field_text:contains(aaa)',
            element:    'tr:has(.oe_list_field_cell:containsExact(bbb)) .oe_list_record_delete button'
        },
        {
            title:      "remove e",
            waitNot:    'tr:has(.oe_list_field_cell:containsExact(bbb))',
            element:    'tr:has(.oe_list_field_cell:containsExact(e)) .oe_list_record_delete button'
        },

        // save
        
        {
            title:      "save discussion",
            waitNot:    'tr:has(.oe_list_field_cell:containsExact(e))',
            element:    'button.oe_form_button_save'
        },

        // check saved data

        {
            title:      "check data 4",
            waitNot:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_char):eq(4)',
        },
        {
            title:      "check data 5",
            waitFor:    'body:has(.oe_list_field_text:containsExact(aaa)):has(.oe_list_field_text:containsExact(c)):has(.oe_list_field_text:containsExact(d))',
        },
        {
            title:      "check data 6",
            waitFor:    '.oe_form_field_one2many tr:has(.oe_list_field_text:containsExact(aaa)):has(.oe_list_field_char:containsExact([test_trigger] Administrator))',
        },
        {
            title:      "check data 7",
            waitFor:    '.oe_form_field_many2many tbody tr:has(.oe_list_field_char):eq(1)',
            waitNot:    '.oe_form_field_many2many tbody tr:has(.oe_list_field_char):eq(2)',
        },

        // edit

        {
            title:      "edit discussion",
            element:    'button.oe_form_button_edit'
        },

        // add message ddd
        
        {
            title:      "create new message ddd",
            waitNot:    '.modal',
            waitFor:    '.oe_list_field_cell:containsExact(d)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "select an other user",
            element:    '.modal .oe_m2o_drop_down_button',
        },
        {
            title:      "select demo user",
            element:    '.modal li a:contains(Demo User)',
        },
        {
            title:      "test one2many's line onchange after many2one",
            waitFor:    '.oe_form_char_content:contains([test_trigger] Demo User)',
        },
        {
            title:      "insert body",
            element:    '.modal textarea.field_text',
            sampleText: 'ddd'
        },
        {
            title:      "save new message ddd",
            waitFor:    '.modal textarea.field_text:propValue(ddd)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // trigger onchange
        
        {
            title:      "blur the one2many",
            waitFor:    '.oe_list_field_cell:containsExact(ddd)',
            element:    '.oe_form_required input',
        },

        // check onchange data

        {
            title:      "check data 8",
            waitFor:    'textarea[name="message_concat"]:propValueContains([test_trigger] Administrator:aaa\n[test_trigger] Administrator:c\n[test_trigger] Administrator:d\n[test_trigger] Demo User:ddd)',
        },
        {
            title:      "check data 9",
            waitFor:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_cell):eq(3)',
            waitNot:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_cell):eq(4)',
        },

        // cancel
        
        {
            title:      "cancel change",
            waitFor:    '.oe_list_field_cell:containsExact(ddd)',
            element:    'a.oe_form_button_cancel',
            onload: function () {
                // remove the window alert (can't click on it with JavaScript tour)
                $('.oe_form_dirty').removeClass('oe_form_dirty');
            }
        },

        /////////////////////////////////////////////////////////////////////////////////////////////
        /////////////////////////////////////////////////////////////////////////////////////////////

        {
            title:      "switch to the second form view to test one2many with editable list",
            waitFor:    '.oe_list_field_cell:eq(3)',
            element:    'a.oe_menu_leaf:contains(Discussions 2)'
        },

        {
            title:      "switch to list view",
            waitFor:    ".oe_list_editable",
            element:    '.oe-cp-switch-list',
        },
        {
            title:      "select previous created record",
            element:    'td[data-field="name"]:contains(test_trigger):last',
        },
        {
            title:      "click on edit",
            element:    '.oe_form_button_edit',
        },

        {
            title:      "click on a field of the editable list to edit content",
            element:    '.oe_list_editable tr[data-id]:eq(1) .oe_list_field_cell:eq(2)',
        },
        {
            title:      "change text value",
            element:    '.oe_form_field[data-fieldname="body"] textarea',
            sampleText: 'ccc'
        },
        {
            title:      "click on a many2one (trigger the line onchange)",
            element:    '.oe_list_editable tr[data-id]:eq(1) .oe_list_field_cell:eq(1)',
        },
        {
            title:      "test one2many's line onchange",
            waitFor:    '.oe_list_editable tr[data-id]:eq(1) .oe_list_field_cell:eq(3):contains(3)',
        },
        {
            title:      "test one2many field not triggered onchange",
            waitNot:    'textarea[name="message_concat"]:propValueContains(ccc)',
        },

        {
            title:      "open the many2one to select an other user",
            element:    '.oe_m2o_drop_down_button',
        },
        {
            title:      "select an other user",
            element:    '.oe_application li a:contains(Demo User)',
        },
        {
            title:      "test one2many's line onchange after many2one",
            waitFor:    '.oe_form_char_content:contains([test_trigger] Demo User)',
        },
        {
            title:      "test one2many field not triggered onchange",
            waitNot:    'textarea[name="message_concat"]:propValueContains(ccc)',
        },
        {
            title:      "change text value",
            element:    '.oe_form_field[data-fieldname="body"] textarea',
            sampleText: 'ccccc'
        },

        // check onchange

        {
            title:      "click outside to trigger one2many onchange",
            waitNot:    'textarea[name="message_concat"]:propValueContains(Demo User)',
            element:    '.oe_form_required input',
        },
        {
            title:      "test one2many onchange",
            waitFor:    'textarea[name="message_concat"]:propValueContains([test_trigger] Demo User:ccccc)',
        },

        {
            title:      "click outside to trigger one2many onchange",
            element:    '.oe_tags .text-arrow',
        },
        {
            title:      "click outside to trigger one2many onchange",
            element:    '.text-label:first',
        },

        {
            title:      "click outside to trigger one2many onchange",
            element:    '.text-label:first',
        },

        // remove record

        {
            title:      "delete the last item in the editable list",
            element:    '.oe_list_record_delete button:visible:last',
        },
        {
            title:      "test one2many onchange after delete",
            waitNot:   'textarea[name="message_concat"]:propValueContains(Administrator:d)',
        },
        
        // save
        
        {
            title:      "save discussion",
            waitNot:    'tr:has(.oe_list_field_cell:containsExact(e))',
            element:    'button.oe_form_button_save'
        },

        // check saved data

        {
            title:      "check data 10",
            waitFor:    '.oe_form_text_content:containsExact([test_trigger] Administrator:aaa\n[test_trigger] Demo User:ccccc)',
        },
        {
            title:      "check data 11",
            waitFor:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_cell):eq(1)',
            waitNot:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_cell):eq(2)',
        },

        // edit

        {
            title:      "edit discussion",
            element:    'button.oe_form_button_edit'
        },

        // add message eee

        {
            title:      "create new message eee",
            waitFor:    'li.active a[data-toggle="tab"]:contains(Messages)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "change text value",
            element:    '.oe_form_field[data-fieldname="body"] textarea',
            sampleText: 'eee'
        },

        // save
        
        {
            title:      "save discussion",
            waitFor:    '.oe_form_field[data-fieldname="body"] textarea:propValueContains(eee)',
            element:    'button.oe_form_button_save'
        },

        // check saved data

        {
            title:      "check data 12",
            waitFor:    '.oe_form_text_content:containsExact([test_trigger] Administrator:aaa\n[test_trigger] Demo User:ccccc\n[test_trigger] Administrator:eee)',
        },
        {
            title:      "check data 13",
            waitFor:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_cell):eq(2)',
            waitNot:    '.oe_form_field_one2many tbody tr:has(.oe_list_field_cell):eq(3)',
        },
    ]
});

});
