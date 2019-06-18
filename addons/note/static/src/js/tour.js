odoo.define('note.tour', function (require) {
'use strict';

var base = require('web_editor.base');
var tour = require('web_tour.tour');

tour.register('note_tour', {
        test: true,
        url: '/web',
        wait_for: base.ready(),
},
    [
        tour.STEPS.SHOW_APPS_MENU_ITEM,
        {
            content: "Create notes here",
            trigger: '.o_app[data-menu-xmlid="note.menu_note_notes"]',
        },
        {
            content: "Add a new note",
            trigger: '.btn-primary.o-kanban-button-new',
        },
        {
            content: "Write the description about your note",
            extra_trigger: '.note-editing-area',
            trigger: '.note-editing-area p',
            run: 'text Awesome Note'
        },
        {
            content: "Save your note",
            trigger: '.btn-primary.o_form_button_save',
        },
        {
            content: "View all of your notes",
            trigger: '.o_menu_brand',
        },
        {
            content: "Edit the note you just created",
            trigger: '.oe_kanban_content span:contains("Awesome Note")',
        },
        {
            content: "Write the description about your note",
            extra_trigger: '.note-editing-area',
            trigger: '.note-editing-area p',
            run: 'text Super Awesome Note'
        },
        {
            content: "Save your changes on the note",
            trigger: '.btn-primary.o_form_button_save',
        },
        {
            content: "Go back to view all of your notes",
            trigger: '.o_menu_brand',
        },
        {
            content: "The edited note is saved here",
            trigger: '.oe_kanban_content span:contains("Super Awesome Note")',
        }
    ]);
});
