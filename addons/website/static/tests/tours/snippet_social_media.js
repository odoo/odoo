/** @odoo-module */

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register('snippet_social_media', {
    test: true,
    url: '/?enable_editor=1',
}, [
    wTourUtils.dragNDrop({id: 's_social_media', name: 'Social Media'}),
    wTourUtils.clickOnSnippet({id: 's_social_media', name: 'Social Media'}),
    {
        content: 'Click on Add New Social Network',
        trigger: 'we-list we-button.o_we_list_add_optional',
    },
    {
        content: 'Change added Option label',
        trigger: 'we-list table input:eq(6)',
        run: 'text https://www.youtu.be/y7TlnAv6cto',
    },
    {
        content: 'Click on the toggle to hide Facebook',
        trigger: 'we-list table we-button.o_we_user_value_widget',
        run: 'click',
    },
    {
        content: 'Drag the facebook link at the end of the list',
        trigger: 'we-list table we-button.o_we_drag_handle',
        position: 'bottom',
        run: "drag_and_drop we-list table tr:last-child",
    },
    // Create a Link for which we don't have an icon to propose.
    {
        content: 'Click on Add New Social Network',
        trigger: 'we-list we-button.o_we_list_add_optional',
    },
    {
        content: 'Change added Option label (2)',
        trigger: 'we-list table input:eq(7)',
        run: 'text https://whatever.it/1EdSw9X',
    },
    // Create a custom instagram link.
    {
        content: 'Click on Add New Social Network',
        trigger: 'we-list we-button.o_we_list_add_optional',
    },
    {
        content: 'Change added Option label (3)',
        trigger: 'we-list table input:eq(8)',
        run: 'text https://instagr.am/odoo.official/',
    },
    {
        content: "Check if the result is correct before removing",
        trigger: ".s_social_media" +
                 ":has(a:eq(0)[href='/website/social/twitter'])" +
                 ":has(a:eq(1)[href='/website/social/linkedin'])" +
                 ":has(a:eq(2)[href='/website/social/youtube'])" +
                 ":has(a:eq(3)[href='/website/social/instagram'])" +
                 ":has(a:eq(4)[href='/website/social/github'])" +
                 ":has(a:eq(5)[href='https://www.youtu.be/y7TlnAv6cto']:has(i.fa-youtube))" +
                 ":has(a:eq(6)[href='https://whatever.it/1EdSw9X']:has(i.fa-pencil))" +
                 ":has(a:eq(7)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
    },
    // Create a custom link, not officially supported, ensure icon is found.
    {
        content: 'Change custom social to unsupported link',
        trigger: 'we-list table input:eq(5)',
        run: 'text https://www.paypal.com/abc',
    },
    {
        content: "Ensure paypal icon is found",
        trigger: ".s_social_media" +
                 ":has(a:eq(5)[href='https://www.paypal.com/abc']:has(i.fa-paypal))",
    },
    {
        content: 'Delete the custom link',
        trigger: 'we-list we-button.o_we_select_remove_option',
        run: 'click',
    },
    {
        content: 'Click on the toggle to show Facebook',
        trigger: 'we-list table we-button.o_we_user_value_widget:not(.active)',
        run: 'click',
    },
    {
        content: "Check if the result is correct after removing",
        trigger: ".s_social_media" +
                 ":has(a:eq(0)[href='/website/social/twitter'])" +
                 ":has(a:eq(1)[href='/website/social/linkedin'])" +
                 ":has(a:eq(2)[href='/website/social/youtube'])" +
                 ":has(a:eq(3)[href='/website/social/instagram'])" +
                 ":has(a:eq(4)[href='/website/social/github'])" +
                 ":has(a:eq(5)[href='/website/social/facebook'])" +
                 ":has(a:eq(6)[href='https://whatever.it/1EdSw9X']:has(i.fa-pencil))" +
                 ":has(a:eq(7)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
    },
    {
        content: 'Change url of the DB instagram link',
        trigger: 'we-list table input:eq(3)',
        run: 'text https://instagram.com/odoo.official/',
    },
    {
        content: 'Save',
        trigger: 'button[data-action=save]',
        run: 'click',
    },
    {
        content: "Wait until save's calls are finished",
        trigger: "body:not(.editor_enable)",
        run: function () {}, // it's a check
    }
]);
