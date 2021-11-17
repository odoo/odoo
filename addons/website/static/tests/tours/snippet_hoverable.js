/** @odoo-module alias=snippet.hoverable **/
'use strict';

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

const columnSelector = '.s_three_columns .col-lg-4:first-child';
const hoverableSelector = `${columnSelector} > .s_hoverable > div`;

const columnEditorSelector = 'we-title:has(span:contains("Column"):not(:contains("Columns")))';
const activationSelector = `${columnEditorSelector} ~ * we-button[data-toggle-hoverable]`;
const originalSelector = `${columnEditorSelector} ~ * we-button:has(:contains("Main"))`;
const previewSelector = `${columnEditorSelector} ~ * we-button:has(:contains("Hover"))`;

function startColumnEditor() {
    return [{
        content: 'Click on first column',
        trigger: columnSelector,
    }, {
        content: 'Check if the column editor is active',
        trigger: columnEditorSelector,
    }];
}

function clickColumnHoverActivate(message = 'Click hoverable activation toggle') {
    return {
        content: message,
        trigger: `${activationSelector} we-checkbox`,
    };
}

function checkColumnHoverDeactivated() {
    return {
        content: 'Check if hoverable is deactivated',
        trigger: columnSelector,
        run: function () {
            if (this.$anchor.find('.s_hoverable').length > 0) {
                console.error('The hoverable overlay is not deactivated');
            }
        },
    };
}

function checkColumnHoverVisibility(status, editMode = true) {
    return [status ? {
        content: 'Check if hoverable is shown',
        trigger: hoverableSelector,
        run: () => {},
    } : {
        content: 'Check if hoverable is hidden',
        trigger: columnSelector,
        run: function () {
            // The offsetParent will be null if the element is not shown.
            if (this.$anchor.find('.s_hoverable > div').is(':hasVisibility')) {
                console.error('The hoverable overlay is not hidden');
            }
        },
    }].concat(editMode ? [{
        content: 'Check if the preview toggle is correctly rendered',
        trigger: `${previewSelector}${status ? '.active' : ':not(.active)'}`,
        run: () => {},
    }] : []);
}

tour.register('snippet_hoverable', {
    test: true,
    url: '?enable_editor=1',
}, [
    wTourUtils.dragNDrop({
        id: 's_three_columns',
        name: 'Columns',
    }),
    ...startColumnEditor(),
    checkColumnHoverDeactivated(),
    clickColumnHoverActivate('Activate hoverable overlay'),
    // Check the preview toggle buttons. When the overlay is activated, it
    // should start in the visible state.
    ...checkColumnHoverVisibility(true),
    {
        content: 'Hide hover effect overlay',
        trigger: originalSelector,
    },
    ...checkColumnHoverVisibility(false),
    {
        content: 'Show hover effect overlay',
        trigger: previewSelector,
    },
    ...checkColumnHoverVisibility(true),
    // Close and reopen the editor to test the cleanForSave and start methods.
    {
        content: 'Close the editor',
        trigger: '#oe_snippets button:contains("Save")',
    },
    ...checkColumnHoverVisibility(false, false),
    {
        content: 'Open the editor',
        trigger: '.o_menu_systray a:contains("Edit")',
    },
    {
        content: 'Wait for the editor to be ready',
        trigger: '#oe_snippets #snippets_menu',
        run: () => {},
    },
    ...startColumnEditor(),
    ...checkColumnHoverVisibility(false),
    // Check if hover effect deactivation removes the DOM element.
    clickColumnHoverActivate('Deactivate hoverable overlay'),
    checkColumnHoverDeactivated(),
]);
