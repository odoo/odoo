import {
    assertPathName,
    clickOnSave,
    getClientActionUrl,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { waitFor } from "@odoo/hoot-dom";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const openPagePropertiesDialog = [
    // FIXME: Needed to prevent a non-deterministic error when click too fast
    //  on the menu item.
    stepUtils.waitIframeIsReady(),
    {
        content: "Open Site backend menu",
        trigger: '[data-menu-xmlid="website.menu_site"]',
        run: "click",
    },
    {
        content: "Open page properties dialog",
        trigger: '[data-menu-xmlid="website.menu_page_properties"]',
        run: "click",
    },
];

const clickOnSaveButtonStep = {
    content: "Click on Save & Close",
    trigger: ".o_form_button_save:enabled",
    run: "click",
};

const openCreatePageDialog = [
    // FIXME: Needed to prevent a non-deterministic error when click too fast
    //  on the menu item.
    stepUtils.waitIframeIsReady(),
    {
        content: "Open create content menu",
        trigger: ".o_new_content_container a",
        run: "click",
    },
    {
        content: "Create a new page",
        trigger: 'a[title="New Page"]',
        run: "click",
    },
];

/**
 * FIXME: This should not be necessary
 * For when tour utils doesn't detect the DOM changes...
 * Seems to happen when watching for an element in the page template selection
 * modal that doesn't exist yet, then appears. I suspect the DOM changes to the
 * modal don't trigger a new search of the `trigger`.
 */
function waitForSelector(selector) {
    return [
        {
            content: `Wait for ${selector}`,
            trigger: "body",
            async run() {
                return waitFor(selector, {
                    timeout: 5000,
                });
            },
        },
    ];
}

function assertPageCanonicalUrlIs(url) {
    return [
        {
            content: `Verify page canonical url is ${url}`,
            trigger: `:visible :iframe head link[rel="canonical"][href$="${url}"]`,
        },
    ];
}
function assertIsInMenu(url) {
    return [
        {
            content: "Verify is in menu",
            trigger: `:visible :iframe #top_menu a[href="${url}"]`,
        },
    ];
}
function assertIsNotInMenu(url) {
    return [
        {
            content: "Verify is not in menu",
            trigger: `:visible :iframe #top_menu:not(:has(a[href="${url}"]))`,
        },
    ];
}

function checkIsTemplate(isTemplate, pageTitle = undefined) {
    return [
        ...openCreatePageDialog,
        ...waitForSelector('a[data-id="custom"]'),
        {
            content: "Go to custom section",
            trigger: 'a[data-id="custom"]',
            run: "click",
        },
        ...(isTemplate
            ? [
                  {
                      content: `Verify template ${pageTitle} exists`,
                      trigger: `:visible .o_page_template .o_page_name:text(${pageTitle})`,
                  },
              ]
            : [
                  ...waitForSelector(".o_website_page_templates_pane .alert-info"),
                  {
                      content: `Verify custom templates section is empty`,
                      trigger: `.o_website_page_templates_pane:not(:has(.o_page_template))`,
                  },
              ]
        ),
        {
            content: "Exit dialog",
            trigger: ".modal-header .btn-close",
            run: "click",
        },
    ];
}

const testEditMenuDialog = [
    {
        content: "Open Edit Menu dialog",
        trigger: '.o_field_widget[name="is_in_menu"] + .btn-link',
        run: "click",
    },
    {
        content: "Check that menu editor was opened",
        trigger: ".oe_menu_editor",
    },
    {
        content: "Close Edit Menu dialog",
        trigger: ".modal:has(.oe_menu_editor) .btn-close",
        run: "click",
    },
];

function testCommonProperties(url, canPublish, modifiedUrl = undefined) {
    if (!modifiedUrl) {
        modifiedUrl = url;
    }

    const steps = {
        setup: [
            {
                content: "Add to menu",
                trigger: "#is_in_menu_0",
                run: "check",
            },
            {
                content: "Set as homepage",
                trigger: "#is_homepage_0",
                run: "check",
            },
        ],
        check: [
            ...assertIsInMenu(modifiedUrl),
            stepUtils.goToUrl(getClientActionUrl("/")),
            ...assertPageCanonicalUrlIs(modifiedUrl),
            stepUtils.goToUrl(getClientActionUrl(modifiedUrl)),
        ],
        teardown: [
            {
                content: "Remove from menu",
                trigger: "#is_in_menu_0",
                run: "uncheck",
            },
            {
                content: "Unset as homepage",
                trigger: "#is_homepage_0",
                run: "uncheck",
            },
        ],
        checkTorndown: [
            ...assertIsNotInMenu(url),
            stepUtils.goToUrl(getClientActionUrl("/")),
            ...assertPageCanonicalUrlIs("/"),
            stepUtils.goToUrl(getClientActionUrl(url)),
            stepUtils.waitIframeIsReady(), // Necessary if it's the last step of the tour
        ],
        finalize() {
            return [
                ...openPagePropertiesDialog,
                ...this.setup,
                ...testEditMenuDialog,
                clickOnSaveButtonStep,
                ...this.check,
                ...openPagePropertiesDialog,
                ...this.teardown,
                clickOnSaveButtonStep,
                ...this.checkTorndown,
            ];
        },
    };

    if (canPublish) {
        steps.setup.push({
            content: "Publish",
            trigger: "#is_published_0",
            run: "check",
        });
        steps.check.push({
            content: "Verify is published",
            trigger: '[data-hotkey="p"] .form-check input:checked',
        });
        steps.teardown.push({
            content: "Unpublish",
            trigger: "#is_published_0",
            run: "uncheck",
        });
        steps.checkTorndown.push({
            content: "Verify is not published",
            trigger: '[data-hotkey="p"] .form-check input:not(:checked)',
        });
    }

    return steps;
}

function testWebsitePageProperties(url, title) {
    const steps = testCommonProperties(url, true, "/cool-page");
    steps.setup.unshift(
        {
            content: "Change page title",
            trigger: "#name_0",
            run: "edit Cool Page",
        },
        {
            content: `Change url to /cool-page`,
            trigger: "#url_0",
            run: `edit cool-page && press Enter`,
        },
        {
            content: "Enable old url redirect",
            trigger: "#redirect_old_url_0",
            run: "check",
        },
        {
            content: "Set redirect type to temporary",
            trigger: "#redirect_type_0",
            run: 'select "302"',
        },
        {
            // TODO: this needs to be tested
            content: "Change date published",
            trigger: "#date_publish_0",
            run: "edit 02/01/2005 01:00:00",
        },
        {
            content: "Don't index",
            trigger: "#website_indexed_0",
            run: "uncheck",
        },
        {
            // TODO: this needs to be tested
            content: "Make visible with password only",
            trigger: "#visibility_0",
            run: 'select "password"',
        },
        {
            content: "Set password to 123",
            trigger: "#visibility_password_display_0",
            run: "edit 123",
        },
        {
            content: "Make it a template",
            trigger: "#is_new_page_template_0",
            run: "check",
        },
    );
    steps.check.push(
        {
            content: "Verify page title",
            trigger: ":visible :iframe head title:text(/Cool Page/)",
        },
        ...assertPageCanonicalUrlIs("/cool-page"),
        stepUtils.goToUrl(getClientActionUrl(url)),
        assertPathName("/cool-page", "body"),
        {
            content: "Verify no index",
            trigger: ':visible :iframe head meta[name="robots"][content="noindex"]',
        },
        ...checkIsTemplate(true, "Cool Page"),
    );
    steps.teardown.unshift(
        {
            content: "Reset page title",
            trigger: "#name_0",
            run: `edit ${title}`,
        },
        {
            content: `Change url back to /new-page`,
            trigger: "#url_0",
            run: `edit new-page && press Enter`,
        },
        {
            content: "Open dependencies link",
            trigger: '[data-bs-html="true"][title="Dependencies"] a',
            run: "click",
        },
        {
            content: "Check that the dependencies popover exists",
            trigger: ".o_page_dependencies",
        },
        {
            content: "Reset date published",
            trigger: "#date_publish_0",
            run: "edit ",
        },
        {
            content: "Do index",
            trigger: "#website_indexed_0",
            run: "check",
        },
        {
            content: "Make visibility Public",
            trigger: "#visibility_0",
            run: 'select ""',
        },
        {
            content: "Remove from templates",
            trigger: "#is_new_page_template_0",
            run: "uncheck",
        },
    );
    steps.checkTorndown.push(
        {
            content: "Verify page title",
            trigger: `:visible :iframe head title:text(/${title}/)`,
        },
        ...assertPageCanonicalUrlIs(url),
        stepUtils.goToUrl(getClientActionUrl(url)),
        assertPathName(url, "body"),
        {
            content: "Verify is indexed",
            trigger: ':visible :iframe head:not(:has(meta[name="robots"][content="noindex"]))',
        },
        ...checkIsTemplate(false),
    );
    return steps;
}

function testClonePage(url, title) {
    const newPageUrl = `${url}-2`; // Automatically set from title
    return [
        ...assertIsInMenu(url),
        ...assertIsNotInMenu(newPageUrl),
        ...openPagePropertiesDialog,
        {
            content: "Click on Clone Page button",
            trigger: ".modal .o_form_buttons_edit .btn:has(.fa-clone)",
            run: "click",
        },
        {
            content: `Name page "${title} 2"`,
            trigger: 'label:text(/Page Name/) + * input[type="text"]',
            run: `edit ${title} 2`,
        },
        {
            content: "Click on dialog's Ok button",
            trigger: ".modal-footer .btn:text(/Ok/)",
            run: "click",
        },
        ...assertPageCanonicalUrlIs(newPageUrl),
        ...assertIsInMenu(newPageUrl),
    ];
}

function testDeletePageDeletesWebsiteMenu(url) {
    return [
        ...assertIsInMenu(url),
        ...openPagePropertiesDialog,
        {
            content: "Click on Delete Page button",
            trigger: ".modal .o_form_buttons_edit .btn:has(.fa-trash)",
            run: "click",
        },
        {
            content: "Check confirmation checkbox",
            trigger: '.modal-body .o-checkbox:has(.text-warning) input[type="checkbox"]',
            run: "check",
        },
        {
            content: "Click dialog's Ok button",
            trigger: ".modal-footer .btn:text(/Ok/)",
            run: "click",
        },
        ...assertIsNotInMenu(url),
    ];
}

registerWebsitePreviewTour(
    "website_page_properties_common",
    {
        test: true,
        url: "/test_view",
    },
    () => [...testCommonProperties("/test_view", false).finalize()],
);

registerWebsitePreviewTour(
    "website_page_properties_can_publish",
    {
        test: true,
        url: "/test_website/model_item/1",
    },
    () => [...testCommonProperties("/test_website/model_item/1", true).finalize()],
);

const TEST_PAGE_TITLE = "New Page";
const TEST_PAGE_URL = "/new-page"; // Automatically set from title
registerWebsitePreviewTour(
    "website_page_properties_website_page",
    {
        test: true,
        url: "/",
    },
    () => [
        ...openCreatePageDialog,
        {
            content: "Use blank template",
            trigger: ".o_page_template .o_button_area",
            run: "click",
        },
        {
            content: "Name page",
            trigger: ".modal-body input",
            run: `edit ${TEST_PAGE_TITLE}`,
        },
        {
            content: "Don't add to menu",
            trigger: ".modal-body .o_switch",
            run: "click",
        },
        {
            content: "Click on Create button",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Wait for editor to open",
            trigger: ".o_website_navbar_hide",
        },
        ...clickOnSave(),
        stepUtils.waitIframeIsReady(),
        ...testWebsitePageProperties(TEST_PAGE_URL, TEST_PAGE_TITLE).finalize(),

        // Add page to menu for testClonePage and
        // testDeletePageDeletesWebsiteMenu
        ...assertIsNotInMenu(TEST_PAGE_URL),
        ...openPagePropertiesDialog,
        {
            content: "Add to menu",
            trigger: "#is_in_menu_0",
            run: "check",
        },
        clickOnSaveButtonStep,
        ...assertIsInMenu(TEST_PAGE_URL),
        stepUtils.waitIframeIsReady(),

        ...testClonePage(TEST_PAGE_URL, TEST_PAGE_TITLE),
        stepUtils.goToUrl(getClientActionUrl(TEST_PAGE_URL)),
        stepUtils.waitIframeIsReady(),
        ...testDeletePageDeletesWebsiteMenu(TEST_PAGE_URL),
    ],
);
