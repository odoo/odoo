/** @odoo-module alias=snippet.popup **/
'use strict';

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

const wrapSelector = '#wrap';
const popupSelector = `${wrapSelector} > .s_popup`;
const popupModalSelector = `${popupSelector} .modal:visible`;
const popupCloseSelector = `.modal-content div.s_popup_close`;

const popupEditorSelector = 'we-title:has(span:contains("Popup"))';

const invisibleElementSelector = '.o_we_invisible_el_panel div:contains("Popup") > i';

function clickPopupClose() {
    return {
        content: `Close the popup`,
        trigger: popupCloseSelector,
    };
}

function checkPopupDeactivated() {
    return {
        content: 'Check if hoverable is deactivated',
        trigger: wrapSelector,
        run: function () {
            if (this.$anchor.find('.s_popup').length > 0) {
                console.error('A popup is still present in the page');
            }
        },
    };
}

function checkPopupVisibility(status) {
    return [status ? {
        content: 'Check if popup is shown',
        trigger: popupModalSelector,
        in_modal: false,
        run: () => {},
    } : {
        content: 'Check if popup is hidden',
        trigger: wrapSelector,
        run: function () {
            // The offsetParent will be null if the element is not shown.
            if (this.$anchor.find('.s_popup .modal')[0].offsetParent !== null) {
                console.error('The popup is not hidden');
            }
        },
    }, {
        content: 'Check if the invisible element is correctly rendered',
        trigger: `${invisibleElementSelector}.${status ? 'fa-eye' : 'fa-eye-slash'}`,
        in_modal: false,
        run: () => {},
    }];
}

function clickTogglePopupVisibility() {
    return {
        content: 'Toggle the visibility of the overlay using the invisible elements panel',
        trigger: invisibleElementSelector,
        in_modal: false,
    };
}

tour.register('snippet_popup', {
    test: true,
    url: '/?enable_editor=1',
}, [
    wTourUtils.dragNDrop({
        id: 's_popup',
        name: 'Popup',
    }),
    {
        content: 'Open the popup editor',
        trigger: popupModalSelector,
        in_modal: false,
    },
    ...checkPopupVisibility(true),
    clickPopupClose(),
    ...checkPopupVisibility(false),
    clickTogglePopupVisibility(),
    ...checkPopupVisibility(true),
    {
        content: 'Remove popup modal',
        trigger: `${popupEditorSelector} we-button.fa-trash`,
        in_modal: false,
    },
    checkPopupDeactivated(),
]);
