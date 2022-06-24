/** @odoo-module */

import wTourUtils from 'website.tour_utils';

const addNewSocialNetwork = function (optionIndex, linkIndex, url) {
    return [{
        content: "Click on Add New Social Network",
        trigger: 'we-list we-button.o_we_list_add_optional',
    },
    {
        content: "Ensure new option is found",
        trigger: `we-list table input:eq(${optionIndex})[data-list-position=${optionIndex}][data-dom-position=${linkIndex}][data-undeletable=false]`,
        run: () => {}, // This is a check.
    },
    {
        content: "Ensure new link is found",
        trigger: `iframe .s_social_media:has(a:eq(${linkIndex})[href='https://www.example.com'])`,
        run: () => {}, // This is a check.
    },
    {
        content: "Change added Option label",
        trigger: `we-list table input:eq(${optionIndex})`,
        run: `text ${url}`,
    },
    {
        content: "Ensure new link is changed",
        trigger: `iframe .s_social_media:has(a:eq(${linkIndex})[href='${url}'])`,
        run: () => {}, // This is a check.
    }];
};

wTourUtils.registerEditionTour('snippet_social_media', {
    test: true,
    url: '/',
    edition: true,
}, [
    wTourUtils.dragNDrop({id: 's_social_media', name: 'Social Media'}),
    wTourUtils.clickOnSnippet({id: 's_social_media', name: 'Social Media'}),
    ...addNewSocialNetwork(6, 6, 'https://www.youtu.be/y7TlnAv6cto'),
    {
        content: 'Click on the toggle to hide Facebook',
        trigger: 'we-list table we-button.o_we_user_value_widget',
        run: 'click',
    },
    {
        content: "Ensure twitter became first",
        trigger: 'iframe .s_social_media:has(a:eq(0)[href="/website/social/twitter"])',
        run: () => {}, // This is a check.
    },
    {
        content: 'Drag the facebook link at the end of the list',
        trigger: 'we-list table we-button.o_we_drag_handle',
        position: 'bottom',
        run: "drag_and_drop we-list table tr:last-child",
    },
    {
        content: 'Check drop completed',
        trigger: 'we-list table input:eq(6)[data-media="facebook"]',
        run: () => {}, // This is a check.
    },
    // Create a Link for which we don't have an icon to propose.
    ...addNewSocialNetwork(7, 6, 'https://whatever.it/1EdSw9X'),
    // Create a custom instagram link.
    ...addNewSocialNetwork(8, 7, 'https://instagr.am/odoo.official/'),
    {
        content: "Check if the result is correct before removing",
        trigger: "iframe .s_social_media" +
                 ":has(a:eq(0)[href='/website/social/twitter'])" +
                 ":has(a:eq(1)[href='/website/social/linkedin'])" +
                 ":has(a:eq(2)[href='/website/social/youtube'])" +
                 ":has(a:eq(3)[href='/website/social/instagram'])" +
                 ":has(a:eq(4)[href='/website/social/github'])" +
                 ":has(a:eq(5)[href='https://www.youtu.be/y7TlnAv6cto']:has(i.fa-youtube))" +
                 ":has(a:eq(6)[href='https://whatever.it/1EdSw9X']:has(i.fa-pencil))" +
                 ":has(a:eq(7)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
        run: () => {}, // This is a check.
    },
    // Create a custom link, not officially supported, ensure icon is found.
    {
        content: 'Change custom social to unsupported link',
        trigger: 'we-list table input:eq(5)',
        run: 'text https://www.paypal.com/abc',
    },
    {
        content: "Ensure paypal icon is found",
        trigger: "iframe .s_social_media" +
                 ":has(a:eq(5)[href='https://www.paypal.com/abc']:has(i.fa-paypal))",
        run: () => {}, // This is a check.
    },
    {
        content: 'Delete the custom link',
        trigger: 'we-list we-button.o_we_select_remove_option',
        run: 'click',
    },
    {
        content: "Ensure custom link was removed",
        trigger: 'iframe .s_social_media:has(a:eq(5)[href="https://whatever.it/1EdSw9X"]:has(i.fa-pencil))',
        run: () => {}, // This is a check.
    },
    {
        content: 'Click on the toggle to show Facebook',
        trigger: 'we-list table we-button.o_we_user_value_widget:not(.active)',
        run: 'click',
    },
    {
        content: "Check if the result is correct after removing",
        trigger: "iframe .s_social_media" +
                 ":has(a:eq(0)[href='/website/social/twitter'])" +
                 ":has(a:eq(1)[href='/website/social/linkedin'])" +
                 ":has(a:eq(2)[href='/website/social/youtube'])" +
                 ":has(a:eq(3)[href='/website/social/instagram'])" +
                 ":has(a:eq(4)[href='/website/social/github'])" +
                 ":has(a:eq(5)[href='/website/social/facebook'])" +
                 ":has(a:eq(6)[href='https://whatever.it/1EdSw9X']:has(i.fa-pencil))" +
                 ":has(a:eq(7)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
        run: () => {}, // This is a check.
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
        trigger: "iframe body:not(.editor_enable)",
        run: function () {}, // it's a check
    }
]);
