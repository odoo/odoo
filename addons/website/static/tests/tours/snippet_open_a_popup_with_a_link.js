odoo.define("website.tour.snippet_open_a_popup_with_a_link", function (require) {
"use strict";

const tour = require('web_tour.tour');
const wTourUtils = require('website.tour_utils');

tour.register('snippet_open_a_popup_with_a_link', {
    test: true,
    url: '/?enable_editor=1',
}, [
    wTourUtils.dragNDrop({
        id: 's_popup',
        name: 'Popup',
    }),
    wTourUtils.clickOnSnippet({
        id: 's_popup',
        name: 'Popup',
    }),
    {
        content: 'Open the select of the display option',
        trigger: 'we-customizeblock-option[class="snippet-option-SnippetPopup"] [data-attribute-name="display"] we-toggler',
        run: 'click',
        in_modal: false,
    },
    {
        content: 'Click on the onClick option',
        trigger: 'we-customizeblock-option[class="snippet-option-SnippetPopup"] [data-name="onclick_opt"]',
        run: 'click',
        in_modal: false,
    },
    {
        content: "Close the popup",
        trigger: '.s_popup_close',
        run: 'click',
    },
    wTourUtils.goBackToBlocks(),
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Double click on the button to open the link dialog",
        trigger: '.s_text_image .btn',
        run: 'dblclick',
    },
    {
        content: "Add the popup id in the link dialog",
        trigger: '#o_link_dialog_url_input',
        run: function () {
            $('#o_link_dialog_url_input')[0].value = '#' + $('#wrap .s_popup .modal')[0].id;
        },
    },
    {
        content: "Save the link dialog",
        trigger: '.modal-content footer .btn-primary',
        run: 'click',
    },
    {
        content: "Save the page",
        trigger: 'button[data-action="save"]',
        run: 'click',
    },
    {
        content: "Click on the button to open the popup",
        extra_trigger: 'body:not(.editor_enable)',
        trigger: '.s_text_image a[data-toggle="modal"]',
        run: 'click',
    },
    {
        content: "Check if the popup is open",
        trigger: '.s_popup .modal.show',
        run: () => null,
        in_modal: false,
    },
]);
});
