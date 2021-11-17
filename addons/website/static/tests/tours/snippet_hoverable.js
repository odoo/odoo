/** @odoo-module alias=snippet.hoverable **/
'use strict';

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

const columnSelector = '.s_three_columns .col-lg-4:first-child';
const hoverableSelector = `${columnSelector} > .s_hoverable > div`;

const columnEditorSelector = 'we-title:has(span:contains("Column"):not(:contains("Columns")))';
const activationSelector = `${columnEditorSelector} ~ * we-button[data-toggle-hoverable]`;
const previewSelector = `${columnEditorSelector} ~ * we-button[data-preview-hoverable]`;

const invisibleElementSelector = '.o_we_invisible_el_panel div:contains("Hover Item") > i';

function clickColumnHoverActivate(message = 'Click hoverable activation toggle') {
    return {
        content: message,
        trigger: `${activationSelector} we-checkbox`,
    };
}

function clickColumnHoverPreview(message = 'Toggle hoverable preview') {
    return {
        content: message,
        trigger: `${previewSelector} i`,
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

function checkColumnHoverVisibility(status) {
    return [status ? {
        content: 'Check if hoverable is shown',
        trigger: hoverableSelector,
        run: () => {},
    } : {
        content: 'Check if hoverable is hidden',
        trigger: columnSelector,
        run: function () {
            // The offsetParent will be null if the element is not shown.
            if (this.$anchor.find('.s_hoverable > div')[0].offsetParent !== null) {
                console.error('The hoverable overlay is not hidden');
            }
        },
    }, {
        content: 'Check if the preview toggle is correctly rendered',
        trigger: `${previewSelector}${status ? '.active' : ''} i.fa-eye`,
        run: () => {},
    }, {
        content: 'Check if the invisible element is correctly rendered',
        trigger: `${invisibleElementSelector}.${status ? 'fa-eye' : 'fa-eye-slash'}`,
        run: () => {},
    }];
}

function clickToggleHoverVisibility() {
    return {
        content: 'Toggle the visibility of the overlay using the invisible elements panel',
        trigger: invisibleElementSelector,
    };
}

tour.register('snippet_hoverable', {
    test: true,
    url: '/?enable_editor=1',
}, [
    wTourUtils.dragNDrop({
        id: 's_three_columns',
        name: 'Columns',
    }),
    {
        content: "Click on first column",
        trigger: '#wrap .s_three_columns .row > :nth-child(1)',
    },
    checkColumnHoverDeactivated(),
    clickColumnHoverActivate('Activate hoverable overlay'),
    ...checkColumnHoverVisibility(true),
    clickColumnHoverPreview('Hide hoverable overlay'),
    ...checkColumnHoverVisibility(false),
    clickColumnHoverActivate('Deactivate hoverable overlay'),
    checkColumnHoverDeactivated(),
    clickColumnHoverActivate('Activate hoverable overlay'),
    ...checkColumnHoverVisibility(true),
    clickToggleHoverVisibility(),
    {
        content: "Check for building blocks menu",
        trigger: '#oe_snippets .o_snippet_search_filter',
    },
    {
        content: "Click on first column",
        trigger: '#wrap .s_three_columns .row > :nth-child(1)',
    },
    ...checkColumnHoverVisibility(false),
    clickColumnHoverPreview('Hide hoverable overlay'),
    ...checkColumnHoverVisibility(true),
    clickColumnHoverActivate('Deactivate hoverable overlay'),
    checkColumnHoverDeactivated(),
]);
