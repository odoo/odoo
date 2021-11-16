/** @odoo-module alias=sticky.overlay **/
'use strict';

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register('sticky_overlay', {
    test: true,
    url: '/?enable_editor=1',
}, [
    wTourUtils.dragNDrop({
        id: 's_text_block',
        name: 'Text',
    }),
    {
        content: "Activate text block editor",
        trigger: '#wrap .s_text_block p:first-child',
    },
    {
        content: "Click on first paragraph node",
        trigger: '#wrap .s_text_block p:first-child',
        run: () => {
            const $node = $('#wrap .s_text_block p:first-child');
            const range = document.createRange();

            range.selectNode($node[0]);
            window.getSelection().addRange(range);
        },
    },
    {
        content: "Animate text",
        trigger: 'div[title="Animate text"]',
    },
    {
        content: "Activate the preview of the text block snippet",
        trigger: 'we-customizeblock-options:nth-child(1)',
        run: () => {
            // The first and top-level editor corresponds to the text block.
            $('we-customizeblock-options:nth-child(1)').mouseenter();
        },
    },
    {
        content: "Check the overlays",
        trigger: '#oe_manipulators',
        run: () => {
            if ($('.oe_overlay.oe_active').length !== 1) {
                console.error('Only the text block overlay should be shown');
            }
        },
    },
    {
        content: "Deactivate the preview of the text block snippet",
        trigger: 'we-customizeblock-options:nth-child(1)',
        run: () => {
            $('we-customizeblock-options:nth-child(1)').mouseleave();
        },
    },
    {
        content: "Check the overlays",
        trigger: '#oe_manipulators',
        run: () => {
            if ($('.oe_overlay.oe_active').length !== 2) {
                console.error('The animated text sticky overlay should have been reactivated');
            }
        },
    },
]);
