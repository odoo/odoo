import { testSwitchWebsite, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";
import { registry } from "@web/core/registry";

// TODO: This part should be moved in a QUnit test
const checkKanbanGroupBy = [
    {
        content: "Click on Kanban View",
        trigger: ".o_cp_switch_buttons .o_kanban",
        run: "click",
    },
    {
        trigger: ".o_kanban_renderer",
    },
    {
        content: "Open search panel menu",
        trigger: ".o_control_panel .o_searchview_dropdown_toggler",
        run: "click",
    },
    {
        content: "Select 'Active' in the select of Custom Group",
        trigger: "select.o_add_custom_group_menu",
        run: "select active",
    },
    {
        trigger: ".o_kanban_renderer .o_kanban_header",
    },
    {
        content: "Click on List View",
        trigger: ".o_cp_switch_buttons .o_list",
        run: "click",
    },
    {
        trigger: ".o_list_renderer",
    },
    {
        content: "Remove applied Group By",
        trigger: ".o_cp_searchview .o_facet_values:contains('Active') .o_facet_remove",
        run: "click",
    },
];

const verifySelectedWebsiteFilter = (website_name) => [
    {
        content: `Check if the search view facet is of ${website_name}`,
        trigger: `.o_searchview_facet .o_facet_value:contains('${website_name}')`,
    },
    {
        content: "Open the search menu dropdown",
        trigger: ".o_searchview_dropdown_toggler",
        run: "click",
    },
    {
        content: `Check if '${website_name}' is selected in the Filters menu`,
        trigger: `.o_filter_menu .o-dropdown-item.selected:contains('${website_name}')`,
    },
    {
        content: "Close the search menu dropdown",
        trigger: ".o_searchview_dropdown_toggler",
        run: "click",
    },
];

const checkWebsiteFilters = [
    // Check if there is a pre-selected website filter
    ...verifySelectedWebsiteFilter("My Website"),
    {
        content: "Check that the homepage is the one of 'My Website'",
        trigger:
            ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home') " +
            "~ .o_data_cell[name=website_id]:contains('My Website')",
    },
    // Check if filters are added for all the websites in Filters column
    {
        content: "Open the search menu dropdown",
        trigger: ".o_searchview_dropdown_toggler",
        run: "click",
    },
    {
        content: "Check if 'My Website' is in the Filters menu",
        trigger: ".o_filter_menu .o-dropdown-item:contains('My Website')",
    },
    {
        content: "Check if 'Test Website' is in the Filters menu",
        trigger: ".o_filter_menu .o-dropdown-item:contains('Test Website')",
    },
    // Check if two website filters can be selected at once
    {
        content: "Select the 'Test Website' filter",
        trigger: ".o_filter_menu .o-dropdown-item:contains('Test Website')",
        run: "click",
    },
    {
        content:
            "Check if the selected website filter now shows both 'My Website' and 'Test Website'",
        trigger:
            ".o_searchview_facet .o_facet_value:contains('My Website') " +
            "~ em.o_facet_values_sep:contains('or') " +
            "~ .o_facet_value:contains('Test Website') ",
    },
    {
        content: "Check that the first homepage is of 'My Website'",
        trigger:
            ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home'):eq(0) " +
            "~ .o_data_cell[name=website_id]:contains('My Website')",
    },
    {
        content: "Check that the second homepage is of 'Test Website'",
        trigger:
            ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home'):eq(1) " +
            "~ .o_data_cell[name=website_id]:contains('Test Website')",
    },
    // Check if removing the website filter shows content from all the websites
    {
        content: "Remove the website filter",
        trigger: ".o_searchview_input_container .o_searchview_facet .o_facet_remove",
        run: "click",
    },
    {
        content: "Check if we got an extra homepage that does not belong to any website",
        trigger:
            ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home'):eq(0) " +
            "~ .o_data_cell[name=website_id]:empty",
    },
];

const deleteSelectedPage = [
    {
        content: "Click on Action",
        trigger: ".o_cp_action_menus button",
        run: "click",
    },
    {
        content: "Click on Delete",
        trigger: '.o-dropdown--menu span:contains("Delete")',
        run: "click",
    },
    {
        content: "Click on I am sure about this",
        trigger: 'main.modal-body input[type="checkbox"]',
        // The loading of the dependencies can take a while and
        // sometimes reach the default 10s timeout
        timeout: 20000,
        run: "click",
    },
    {
        content: "Click on OK",
        trigger: ".modal-content footer button.btn-primary:not([disabled])",
        run: "click",
    },
];
const homePage = 'tr:contains("Home")';

const duplicateSinglePage = [
    {
        content: "Click on checkbox",
        trigger:
            '.o_list_renderer tr:contains("/test-duplicate") td.o_list_record_selector input[type="checkbox"]',
        run: "click",
    },
    {
        content: "Click on Action button",
        trigger: ".o_cp_action_menus button",
        run: "click",
    },
    {
        content: "Click on Duplicate",
        trigger: '.o-dropdown--menu span:contains("Duplicate")',
        run: "click",
    },
    {
        content: "Put your website name as 'Test Duplicate' here",
        trigger: 'main.modal-body input[type="text"]',
        run: "edit Test Duplicate",
    },
    {
        content: "Click on OK",
        trigger: ".modal-footer button.btn-primary",
        run: "click",
    },
    {
        content: "Wait for the Test Duplicate to appear",
        trigger: "td:contains('/test-duplicate-1')",
    },
];

const duplicateMultiplePage = [
    {
        content: "Click on checkbox",
        trigger:
            '.o_list_renderer tr:contains("/test-duplicate") td.o_list_record_selector input[type="checkbox"]',
        run: "click",
    },
    {
        content: "Click on checkbox",
        trigger:
            '.o_list_renderer tr:contains("/test-duplicate-1") td.o_list_record_selector input[type="checkbox"]',
        run: "click",
    },
    {
        content: "Click on Action button",
        trigger: ".o_cp_action_menus button",
        run: "click",
    },
    {
        content: "Click on Duplicate",
        trigger: '.o-dropdown--menu span:contains("Duplicate")',
        run: "click",
    },
    {
        content: "Put your website name as 'Test Duplicate' here",
        trigger: 'main.modal-body input[type="text"]',
        run: "edit Test Duplicate",
    },
    {
        content: "Click on OK",
        trigger: ".modal-footer button.btn-primary",
        run: "click",
    },
];

registerWebsitePreviewTour(
    "website_page_manager",
    {
        url: "/",
    },
    () => [
        {
            content: "Click on Site",
            trigger: 'button.dropdown-toggle[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Click on Pages",
            trigger: 'a.dropdown-item[data-menu-xmlid="website.menu_website_pages_list"]',
            run: "click",
        },
        ...checkKanbanGroupBy,
        ...checkWebsiteFilters,
        {
            content: "Open the search menu dropdown",
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            content: "Select 'My Website' filter",
            trigger: ".o_filter_menu .o-dropdown-item:contains('My Website')",
            run: "click",
        },
        {
            content: "Click on Home Page",
            trigger: `.o_list_renderer ${homePage} td.o_list_record_selector input[type="checkbox"]`,
            run: "click",
        },
        ...deleteSelectedPage,
        {
            content: "Check that the page has been removed",
            trigger: `.o_list_renderer:not(:has(${homePage}))`,
        },
        {
            content: "Click on All Pages",
            trigger: '.o_list_renderer thead input[type="checkbox"]',
            run: "click",
        },
        ...deleteSelectedPage,
        {
            content: "Check that all pages have been removed",
            trigger: ".o_list_renderer tbody:not(:has([data-id]))",
        },
    ]
);

registerWebsitePreviewTour(
    "website_page_manager_session_forced",
    {
        url: "/",
    },
    () => [
        ...testSwitchWebsite("Test Website"),
        {
            content: "Click on Site",
            trigger: 'button.dropdown-toggle[data-menu-xmlid="website.menu_site"]',
            run: " click",
        },
        {
            content: "Click on Pages",
            trigger: 'a.dropdown-item[data-menu-xmlid="website.menu_website_pages_list"]',
            run: " click",
        },
        {
            content: "Check that the homepage is the one of Test Website",
            trigger:
                ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home') " +
                "~ .o_data_cell[name=website_id]:contains('Test Website')",
        },
        ...verifySelectedWebsiteFilter("Test Website"),
    ]
);

registry.category("web_tour.tours").add("website_page_manager_direct_access", {
    url: "/odoo/action-website.action_website_pages_list",
    steps: () => [
        {
            content: "Check that the homepage is the one of Test Website",
            trigger:
                ".o_list_table .o_data_row .o_data_cell[name=name]:contains('Home') " +
                "~ .o_data_cell[name=website_id]:contains('Test Website')",
        },
        ...verifySelectedWebsiteFilter("Test Website"),
    ],
});

registerWebsitePreviewTour(
    "website_clone_pages",
    {
        url: "/",
    },
    () => [
        {
            content: "Click on Site",
            trigger: 'button.dropdown-toggle[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Click on Pages",
            trigger: 'a.dropdown-item[data-menu-xmlid="website.menu_website_pages_list"]',
            run: "click",
        },
        ...duplicateSinglePage,
        ...duplicateMultiplePage,
        {
            trigger: "td:contains('/test-duplicate-2-1')",
        },
    ]
);
