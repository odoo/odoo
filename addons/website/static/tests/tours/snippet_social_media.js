/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

// TODO: Remove following steps once fix of task-3212519 is done.
// Those steps are preventing a race condition to happen in the meantime: when
// the tour was clicking on the toggle to hide facebook in the next step, it
// would actually "ignore" the result of the click on the toggle and would just
// consider the action of focusing out the input.
const socialRaceConditionClass = 'social_media_race_condition';
const preventRaceConditionStep = [{
    content: "Wait a few ms to avoid race condition",
    // Ensure the class is remove from previous call of those steps
    extra_trigger: `body:not(.${socialRaceConditionClass})`,
    trigger: 'iframe .s_social_media',
    run() {
        setTimeout(() => {
            document.body.classList.add(socialRaceConditionClass);
        }, 500);
    }
}, {
    content: "Check the race condition class is added after a few ms",
    trigger: `body.${socialRaceConditionClass}`,
    run() {
        document.body.classList.remove(socialRaceConditionClass);
    }
}];

const replaceIconByImage = function (url) {
    return [{
        content: "Replace the icon by an image",
        trigger: `iframe .s_social_media a[href='${url}'] i.fa`,
        run: "dblclick",
    },
    {
        content: "Go to the Images tab in the media dialog",
        trigger: ".o_select_media_dialog .o_notebook_headers .nav-item a:contains('Images')",
    },
    {
        content: "Select the image",
        trigger: ".o_select_media_dialog img[title='s_banner_default_image.jpg']",
    },
    ...preventRaceConditionStep,
    ];
};

const addNewSocialNetwork = function (optionIndex, linkIndex, url, replaceIcon = false) {
    const replaceIconByImageSteps = replaceIcon ? replaceIconByImage("https://www.example.com") : [];
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
    ...replaceIconByImageSteps,
    {
        content: "Change added Option label",
        trigger: `we-list table input:eq(${optionIndex})`,
        run: `text_blur ${url}`,
    },
    {
        content: "Ensure new link is changed",
        trigger: `iframe .s_social_media:has(a:eq(${linkIndex})[href='${url}'])`,
        run: () => {}, // This is a check.
    },
    ...preventRaceConditionStep,
    ];
};

wTourUtils.registerWebsitePreviewTour('snippet_social_media', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop({id: 's_social_media', name: 'Social Media'}),
    wTourUtils.clickOnSnippet({id: 's_social_media', name: 'Social Media'}),
    ...addNewSocialNetwork(7, 7, 'https://www.youtu.be/y7TlnAv6cto'),
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
        run: "drag_and_drop_native we-list table tr:last-child",
    },
    {
        content: 'Check drop completed',
        trigger: 'we-list table input:eq(7)[data-media="facebook"]',
        run: () => {}, // This is a check.
    },
    ...preventRaceConditionStep,
    // Create a Link for which we don't have an icon to propose.
    ...addNewSocialNetwork(8, 7, 'https://whatever.it/1EdSw9X'),
    // Create a custom instagram link.
    ...addNewSocialNetwork(9, 8, 'https://instagr.am/odoo.official/'),
    {
        content: "Check if the result is correct before removing",
        trigger: "iframe .s_social_media" +
                 ":has(a:eq(0)[href='/website/social/twitter'])" +
                 ":has(a:eq(1)[href='/website/social/linkedin'])" +
                 ":has(a:eq(2)[href='/website/social/youtube'])" +
                 ":has(a:eq(3)[href='/website/social/instagram'])" +
                 ":has(a:eq(4)[href='/website/social/github'])" +
                 ":has(a:eq(5)[href='/website/social/tiktok'])" +
                 ":has(a:eq(6)[href='https://www.youtu.be/y7TlnAv6cto']:has(i.fa-youtube))" +
                 ":has(a:eq(7)[href='https://whatever.it/1EdSw9X']:has(i.fa-pencil))" +
                 ":has(a:eq(8)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
        run: () => {}, // This is a check.
    },
    // Create a custom link, not officially supported, ensure icon is found.
    {
        content: 'Change custom social to unsupported link',
        trigger: 'we-list table input:eq(6)',
        run: 'text_blur https://www.paypal.com/abc',
    },
    {
        content: "Ensure paypal icon is found",
        trigger: "iframe .s_social_media" +
                 ":has(a:eq(6)[href='https://www.paypal.com/abc']:has(i.fa-paypal))",
        run: () => {}, // This is a check.
    },
    ...preventRaceConditionStep,
    {
        content: 'Delete the custom link',
        trigger: 'we-list we-button.o_we_select_remove_option',
        run: 'click',
    },
    {
        content: "Ensure custom link was removed",
        trigger: 'iframe .s_social_media:has(a:eq(6)[href="https://whatever.it/1EdSw9X"]:has(i.fa-pencil))',
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
                 ":has(a:eq(5)[href='/website/social/tiktok'])" +
                 ":has(a:eq(6)[href='/website/social/facebook'])" +
                 ":has(a:eq(7)[href='https://whatever.it/1EdSw9X']:has(i.fa-pencil))" +
                 ":has(a:eq(8)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
        run: () => {}, // This is a check.
    },
    {
        content: 'Change url of the DB instagram link',
        trigger: 'we-list table input:eq(3)',
        run: 'text_blur https://instagram.com/odoo.official/',
    },
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Check if we can still change custom icons",
        trigger: 'iframe .s_social_media a[href="https://whatever.it/1EdSw9X"] i.fa-pencil',
    },
    {
        content: "Click on replace media",
        trigger: "[data-replace-media='true']",
    },
    {
        content: "Select a new icon",
        trigger: '.o_select_media_dialog .fa-heart',
    },
    {
        content: "Check if the result is correct after setting the icon",
        trigger: "iframe .s_social_media" +
                 ":has(a:eq(0)[href='/website/social/twitter'])" +
                 ":has(a:eq(1)[href='/website/social/linkedin'])" +
                 ":has(a:eq(2)[href='/website/social/youtube'])" +
                 ":has(a:eq(3)[href='/website/social/instagram'])" +
                 ":has(a:eq(4)[href='/website/social/github'])" +
                 ":has(a:eq(5)[href='/website/social/tiktok'])" +
                 ":has(a:eq(6)[href='/website/social/facebook'])" +
                 ":has(a:eq(7)[href='https://whatever.it/1EdSw9X']:has(i.fa-heart))" +
                 ":has(a:eq(8)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
        isCheck: true,
    },
    // Create a social network but replace its icon by an image before setting
    // the link (`replaceIcon` parameter set to `true`).
    ...addNewSocialNetwork(9, 9, "https://google.com", true),
    // Create a social network after replacing the first icon by an image.
    ...replaceIconByImage("/website/social/twitter"),
    ...addNewSocialNetwork(10, 10, "https://facebook.com"),
    {
        content: "Check if the result is correct after adding images",
        trigger: "iframe .s_social_media" +
                 ":has(a:eq(0)[href='/website/social/twitter']:has(img))" +
                 ":has(a:eq(9)[href='https://google.com']:has(img))" +
                 ":has(a:eq(10)[href='https://facebook.com']:has(img))",
        run: () => {}, // This is a check.
    },
    ...wTourUtils.clickOnSave(),
]);
