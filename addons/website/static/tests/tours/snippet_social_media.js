import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    unfoldOptionsGroup,
} from "@website/js/tours/tour_utils";

// TODO: Remove following steps once fix of task-3212519 is done.
// Those steps are preventing a race condition to happen in the meantime: when
// the tour was clicking on the toggle to hide facebook in the next step, it
// would actually "ignore" the result of the click on the toggle and would just
// consider the action of focusing out the input.
const socialRaceConditionClass = "social_media_race_condition";
const preventRaceConditionStep = [
    {
        trigger: `body:not(.${socialRaceConditionClass})`,
    },
    {
        content: "Wait a few ms to avoid race condition",
        // Ensure the class is remove from previous call of those steps
        trigger: ":iframe .s_social_media",
        run() {
            setTimeout(() => {
                document.body.classList.add(socialRaceConditionClass);
            }, 500);
        },
    },
    {
        content: "Check the race condition class is added after a few ms",
        trigger: `body.${socialRaceConditionClass}`,
        run() {
            document.body.classList.remove(socialRaceConditionClass);
        },
    },
];

const replaceIconByImage = function (url) {
    return [
        {
            content: "Replace the icon by an image",
            trigger: `:iframe .s_social_media a[href='${url}'] i.fa`,
            run: "dblclick",
        },
        {
            content: "Go to the Images tab in the media dialog",
            trigger: ".o_select_media_dialog .o_notebook_headers .nav-item button:contains('Images')",
            run: "click",
        },
        {
            content: "Select the image",
            trigger:
                ".o_select_media_dialog .o_button_area[aria-label='s_banner_default_image.jpg']",
            run: "click",
        },
        ...preventRaceConditionStep,
    ];
};

const addNewSocialNetwork = function (optionIndex, url, replaceIcon = false) {
    const replaceIconByImageSteps = replaceIcon
        ? [...replaceIconByImage("https://www.example.com"), ...unfoldOptionsGroup("Social Media")]
        : [];
    return [
        {
            content: "Click on Add New Social Network",
            trigger:
                "div[data-container-title='Social Media'] button[data-action-id='addSocialMediaLink']",
            run: "click",
        },
        {
            content: "Ensure new option is found",
            trigger: `.o_social_media_list tr:eq(${optionIndex}):has(div[data-action-id="editSocialMediaLink"])`,
        },
        {
            content: "Ensure new link is found",
            trigger: `:iframe .s_social_media:has(a:eq(${optionIndex})[href='https://www.example.com'])`,
        },
        ...replaceIconByImageSteps,
        {
            content: "Change added Option label",
            trigger: `.o_social_media_list tr:eq(${optionIndex}) input`,
            run: `edit ${url} && click body`,
        },
        {
            content: "Ensure new link is changed",
            trigger: `:iframe .s_social_media:has(a:eq(${optionIndex})[href='${url}'])`,
        },
        ...preventRaceConditionStep,
    ];
};

registerWebsitePreviewTour(
    "snippet_social_media",
    {
        undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_social_media", name: "Social Media" }),
        ...clickOnSnippet({ id: "s_social_media", name: "Social Media" }),
        ...addNewSocialNetwork(8, "https://www.youtu.be/y7TlnAv6cto"),
        {
            content: "Remove the Facebook link from the snippet",
            trigger: ".o_social_media_list button[data-action-id='deleteSocialMediaLink']",
            run: "click",
        },
        {
            content: "Ensure twitter became first",
            trigger:
                ':iframe .s_social_media:has(a:eq(0)[href="https://www.twitter.com/your-page"])',
        },
        {
            content: "Drag the twitter link at the end of the list",
            trigger: ".o_social_media_list button.o_drag_handle",
            tooltipPosition: "bottom",
            run: "drag_and_drop .o_social_media_list tr:last-child",
        },
        ...preventRaceConditionStep,
        // Create a Link for which we don't have an icon to propose.
        ...addNewSocialNetwork(8, "https://whatever.it/1EdSw9X"),
        // Create a custom instagram link.
        ...addNewSocialNetwork(9, "https://instagr.am/odoo.official/"),
        {
            content: "Check if the result is correct before removing",
            trigger:
                ":iframe .s_social_media" +
                ":has(a:eq(0)[href='https://www.linkedin.com/your-page'])" +
                ":has(a:eq(1)[href='https://www.youtube.com/your-page'])" +
                ":has(a:eq(2)[href='https://www.instagram.com/your-page'])" +
                ":has(a:eq(3)[href='https://www.github.com/your-page'])" +
                ":has(a:eq(4)[href='https://www.tiktok.com/your-page'])" +
                ":has(a:eq(5)[href='https://www.discord.com/your-page'])" +
                ":has(a:eq(6)[href='https://www.youtu.be/y7TlnAv6cto']:has(i.fa-youtube-play))" +
                ":has(a:eq(7)[href='https://www.twitter.com/your-page'])" +
                ":has(a:eq(8)[href='https://whatever.it/1EdSw9X']:has(i.fa-pencil))" +
                ":has(a:eq(9)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
        },
        // Create a custom link, not officially supported, ensure icon is found.
        {
            content: "Change custom social to unsupported link",
            trigger: ".o_social_media_list tr:eq(6) input",
            run: "edit https://www.paypal.com/abc && click body",
        },
        {
            content: "Ensure paypal icon is found",
            trigger:
                ":iframe .s_social_media" +
                ":has(a:eq(6)[href='https://www.paypal.com/abc']:has(i.fa-paypal))",
        },
        ...preventRaceConditionStep,
        {
            content: "Delete the custom link",
            trigger: ".o_social_media_list tr:eq(6) button[data-action-id='deleteSocialMediaLink']",
            run: "click",
        },
        {
            content: "Ensure custom link was removed",
            trigger:
                ':iframe .s_social_media:has(a:eq(7)[href="https://whatever.it/1EdSw9X"]:has(i.fa-pencil))',
        },
        {
            content: "Check if the result is correct after removing",
            trigger:
                ":iframe .s_social_media" +
                ":has(a:eq(0)[href='https://www.linkedin.com/your-page'])" +
                ":has(a:eq(1)[href='https://www.youtube.com/your-page'])" +
                ":has(a:eq(2)[href='https://www.instagram.com/your-page'])" +
                ":has(a:eq(3)[href='https://www.github.com/your-page'])" +
                ":has(a:eq(4)[href='https://www.tiktok.com/your-page'])" +
                ":has(a:eq(5)[href='https://www.discord.com/your-page'])" +
                ":has(a:eq(6)[href='https://www.twitter.com/your-page'])" +
                ":has(a:eq(7)[href='https://whatever.it/1EdSw9X']:has(i.fa-pencil))" +
                ":has(a:eq(8)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
        },
        {
            content: "Change url of the DB instagram link",
            trigger: ".o_social_media_list tr:eq(2) input",
            run: "edit https://instagram.com/odoo.official/ && click body",
        },
        ...preventRaceConditionStep,
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet({
            id: "s_social_media",
            name: "Social Media",
        }),
        {
            content: "Check if we can still change custom icons",
            trigger: ':iframe .s_social_media a[href="https://whatever.it/1EdSw9X"] i.fa-pencil',
            run: "dblclick",
        },
        {
            content: "Select a new icon",
            trigger: ".o_select_media_dialog .fa-heart",
            run: "click",
        },
        {
            content: "Check if the result is correct after setting the icon",
            trigger:
                ":iframe .s_social_media" +
                ":has(a:eq(0)[href='https://www.linkedin.com/your-page'])" +
                ":has(a:eq(1)[href='https://www.youtube.com/your-page'])" +
                ":has(a:eq(2)[href='https://instagram.com/odoo.official/'])" +
                ":has(a:eq(3)[href='https://www.github.com/your-page'])" +
                ":has(a:eq(4)[href='https://www.tiktok.com/your-page'])" +
                ":has(a:eq(5)[href='https://www.discord.com/your-page'])" +
                ":has(a:eq(6)[href='https://www.twitter.com/your-page'])" +
                ":has(a:eq(7)[href='https://whatever.it/1EdSw9X']:has(i.fa-heart))" +
                ":has(a:eq(8)[href='https://instagr.am/odoo.official/']:has(i.fa-instagram))",
        },
        ...unfoldOptionsGroup("Social Media"),
        // Create a social network but replace its icon by an image before setting
        // the link (`replaceIcon` parameter set to `true`).
        ...addNewSocialNetwork(9, "https://google.com", true),
        // Create a social network after replacing the first icon by an image.
        ...replaceIconByImage("https://www.linkedin.com/your-page"),
        ...unfoldOptionsGroup("Social Media"),
        ...addNewSocialNetwork(10, "https://facebook.com"),
        {
            content: "Check if the result is correct after adding images",
            trigger:
                ":iframe .s_social_media" +
                ":has(a:eq(0)[href='https://www.linkedin.com/your-page']:has(img))" +
                ":has(a:eq(9)[href='https://google.com']:has(img))" +
                ":has(a:eq(10)[href='https://facebook.com']:has(img))",
        },
        ...clickOnSave(),
    ]
);
