odoo.define('web_editor.tour.snippets', function (require) {
'use strict';

var Tour = require('web.Tour');
require('web_editor.base');

Tour.register({
    id:   'web_editor_snippets',
    name: "Test editor snippets",
    mode: 'test',
    path: function () {
        return '/web_editor/field/test?callback=FieldTextHtml_0&enable_editor=1&field=many2many';
    },
    steps: [
        {
            title:      "wait web client",
            waitFor:    'div[data-oe-model="web_editor.converter.test"]'
        },
        {
            title:     "reload page with new id",
            waitFor:   'div[data-oe-type="many2many"]',
            onload: function () {
                if (!window.location.href.match('res_id')) {
                    window.location.href = '/web_editor/field/test?callback=FieldTextHtml_0&enable_editor=1&field=many2many&res_id='+$('div[data-oe-type="many2many"]').data('oe-id');
                }
            }
        },
        {
            title:     "click on many2many",
            element:   'div[data-oe-type="many2many"]',
        },
        {
            title:     "insert name 'aaa'",
            element:   ".o_editor_many2many input",
            waitFor:   '.o_editor_many2many ul li:eq(0)',
            waitNot:   '.o_editor_many2many ul li:eq(1)',
            sampleText: 'aaa',
        },
        {
            title:     "create or select 'aaa' tag",
            element:   ".o_editor_many2many ul *:containsExactCase(aaa)",
        },
        {
            title:     "check 'aaa' options insertion",
            waitFor:   '.o_editor_many2many ul li a[data-name="aaa"].o_selected',
        },
        {
            title:     "check 'aaa' field insertion",
            waitFor:   'div[data-oe-field="many2many"][contenteditable="false"] span.label:containsExactCase(aaa)',
        },
        {
            title:     "insert new name to create tag",
            element:   ".o_editor_many2many input",
            waitFor:   '.o_editor_many2many ul li:eq(1)',
            waitNot:   '.o_editor_many2many ul li:eq(2)',
            sampleText: new Date().getTime(),
        },
        {
            title:     "create or select 'aaa' tag",
            element:   ".o_editor_many2many a.o_create",
        },
        {
            title:     "remove 'aaa' tag",
            waitFor:   'div[data-oe-field="many2many"] span:eq(1)',
            element:   '.o_editor_many2many ul li a[data-name="aaa"] .fa-close',
        },
        {
            title:     "undo",
            waitNot:   '.o_editor_many2many ul li a[data-name="aaa"].o_selected, div[data-oe-field="many2many"] span:eq(1)',
            waitFor:   'div[data-oe-field="many2many"] span:eq(0)',
            element:   '#web_editor-top-edit .note-popover .note-air-popover button[data-event="undo"]',
            onload: function () {
                $('#web_editor-top-edit form').show();
            }
        },
        {
            title:     "check undo",
            waitFor:   'div[data-oe-field="many2many"] span:eq(1)',
            element:   '#web_editor-top-edit button[data-action="save"]',
        },
        {
            title:     "check saved values",
            waitNot:   '#web_editor-top-edit, div[data-oe-field="many2many"], #wrap span:eq(2)',
            waitFor:   '#wrap:has(span:containsExactCase(aaa)):has(span:containsRegex(/^[0-9]+$/))',
        },
    ]
});

});
