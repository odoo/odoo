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
            title:      "create new message",
            waitFor:    '.oe_form_required input:propValue(test)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body",
            element:    'textarea.field_text',
            sampleText: 'a'
        },
        {
            title:      "create new message",
            waitFor:    'textarea.field_text:propValue(a)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // add message b
        
        {
            title:      "create new message",
            waitFor:    '.oe_list_field_cell',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body",
            element:    'textarea.field_text',
            sampleText: 'b'
        },
        {
            title:      "create new message",
            waitFor:    'textarea.field_text:propValue(b)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // change title to trigger on change

        {
            title:      "insert title",
            waitFor:    '.oe_list_field_cell:eq(2)',
            element:    '.oe_form_required input',
            sampleText: 'test trigger'
        },

        // change message b
        
        {
            title:      "edit message b",
            waitFor:    'tr:has(.oe_list_field_cell):not(:has(.oe_list_record_selector)):eq(1) .oe_list_field_cell:contains([test trigger] )',
            waitNot:    'tr:has(.oe_list_field_cell):not(:has(.oe_list_record_selector)):eq(2)',
            element:    '.oe_list_field_cell:containsExact(b)'
        },
        {
            title:      "change the body",
            element:    'textarea.field_text',
            sampleText: 'bbb'
        },
        {
            title:      "save changes",
            waitFor:    'textarea.field_text:propValue(bbb)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // add message c
        
        {
            title:      "create new message",
            waitNot:    '.modal',
            waitFor:    'tr:has(.oe_list_field_cell):not(:has(.oe_list_record_selector)):eq(1) .oe_list_field_text:contains(bbb)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body",
            element:    'textarea.field_text',
            sampleText: 'c'
        },
        {
            title:      "create new message",
            waitFor:    'textarea.field_text:propValue(c)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // add participants

        {
            title:      "change tab to Participants",
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
            waitFor:    '.oe_form_field_one2many tr:has(.oe_list_field_text:containsExact(bbb)):has(.oe_list_field_char:containsExact([test trigger] Administrator))',
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
            title:      "create new message",
            waitFor:    'li.active a[data-toggle="tab"]:contains(Messages)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body",
            element:    'textarea.field_text',
            sampleText: 'd'
        },
        {
            title:      "create new message",
            waitFor:    'textarea.field_text:propValue(d)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // add message e
        
        {
            title:      "create new message",
            waitFor:    '.oe_list_field_cell:containsExact(d)',
            element:    '.oe_form_field_one2many_list_row_add a'
        },
        {
            title:      "insert body",
            element:    'textarea.field_text',
            sampleText: 'e'
        },
        {
            title:      "create new message",
            waitFor:    'textarea.field_text:propValue(e)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // change message a

        {
            title:      "create new message",
            waitFor:    '.oe_list_field_cell:containsExact(e)',
            element:    '.oe_list_field_cell:containsExact(a)'
        },
        {
            title:      "change the body",
            element:    'textarea.field_text',
            sampleText: 'aaa'
        },
        {
            title:      "save changes",
            waitFor:    'textarea.field_text:propValue(aaa)',
            element:    '.oe_abstractformpopup-form-save'
        },

        // remove
        
        {
            title:      "remove b",
            waitFor:    '.oe_list_field_text:contains(aaa)',
            waitNot:    '.modal',
            element:    'tr:has(.oe_list_field_cell:containsExact(bbb)) .oe_list_record_delete button'
        },
        {
            title:      "remove e",
            waitNot:    'tr:has(.oe_list_field_cell:containsExact(bbb))',
            element:    'tr:has(.oe_list_field_cell:containsExact(e)) .oe_list_record_delete button'
        },
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
            waitFor:    '.oe_form_field_one2many tr:has(.oe_list_field_text:containsExact(aaa)):has(.oe_list_field_char:containsExact([test trigger] Administrator))',
        },
        {
            title:      "check data 7",
            waitFor:    '.oe_form_field_many2many tbody tr:has(.oe_list_field_char):eq(1)',
            waitNot:    '.oe_form_field_many2many tbody tr:has(.oe_list_field_char):eq(2)',
        },

        {
            title:      "finish",
            waitFor:    '.oe_list_field_cell:eq(3)',
        },
    ]
});

});
