import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
    selectElementInWeSelectWidget,
    selectFullText,
} from "@website/js/tours/tour_utils";

function withoutContains(steps) {
    for (const step of steps) {
        step.trigger = step.trigger.replaceAll(/:contains\(.*\)/g, "");
    }
    return steps;
}

registerWebsitePreviewTour(
    "translation_single_language",
    {
        url: "/",
    },
    () => [{
            content: "Open +New content",
            trigger: ".o_menu_systray .o_menu_systray_item.o_new_content_container",
            run: "click",
        },
        {
            content: "Create a New page",
            trigger: ".o_new_content_element button:has(.fa-file-o)",
            run: "click",
        },
        {
            content: "Select Blank page",
            trigger: ".o_page_template:has(div.text-muted) .o_button_area:not(:visible)",
            run: "click",
        },
        {
            content: "Page name",
            trigger: ".modal-dialog .o_website_dialog input",
            run: "edit Test",
        },
        {
            content: "Confirm creation",
            trigger: ".modal-dialog .o_website_dialog .btn-primary",
            run: "click",
        },
        ...insertSnippet({
            id: "s_banner",
            name: "Banner",
            groupName: "Intro",
        }),
        ...withoutContains(clickOnSave()),
        {
            content: "Open Site menu",
            trigger: ".o_menu_sections [data-menu-xmlid='website.menu_site']",
            run: "click",
        },
        {
            content: "Open Site menu",
            trigger: ".o-overlay-item .dropdown-item[data-menu-xmlid='website.menu_ace_editor']",
            run: "click",
        },
        {
            content: "Edit anyway",
            trigger: ".o_resource_editor_wrapper [role='alert'] button.btn-link",
            run: "click",
        },
        {
            content: "Change text",
            trigger: 'div.ace_line .ace_xml:contains("oe_structure")',
            run() {
                ace.edit(document.querySelector("#resource-editor div"))
                    .getSession()
                    .insert({row: 8, column: 1}, '<p>More text</p>\n');
            },
        },
        {
            content: "Save the html editor",
            trigger: ".o_resource_editor button.btn-primary",
            run: "click",
        },
        {
            content: "Close the html editor",
            trigger: ".o_resource_editor button.btn-secondary",
            run: "click",
        },
        {
            content: "Page is updated",
            trigger: ":iframe body:contains(More text)",
        },
        // TODO xml record
    ]
);

// TODO multi language
registerWebsitePreviewTour(
    "translation_multi_language",
    {
        url: "/",
    },
    () => [{
            content: "Open +New content",
            trigger: ".o_menu_systray .o_menu_systray_item.o_new_content_container",
            run: "click",
        },
        {
            content: "Create a New page",
            trigger: ".o_new_content_element button:has(.fa-file-o)",
            run: "click",
        },
        {
            content: "Select Blank page",
            trigger: ".o_page_template:has(div.text-muted) .o_button_area:not(:visible)",
            run: "click",
        },
        {
            content: "Page name",
            trigger: ".modal-dialog .o_website_dialog input",
            run: "edit Test",
        },
        {
            content: "Confirm creation",
            trigger: ".modal-dialog .o_website_dialog .btn-primary",
            run: "click",
        },
        ...insertSnippet({
            id: "s_banner",
            name: "Banner",
            groupName: "Intro",
        }),
        ...withoutContains(clickOnSave()),
        {
            content: "Open Site menu",
            trigger: ".o_menu_sections [data-menu-xmlid='website.menu_site']",
            run: "click",
        },
        {
            content: "Open Site menu",
            trigger: ".o-overlay-item .dropdown-item[data-menu-xmlid='website.menu_ace_editor']",
            run: "click",
        },
        {
            content: "Edit anyway",
            trigger: ".o_resource_editor_wrapper [role='alert'] button.btn-link",
            run: "click",
        },
        {
            content: "Change text",
            trigger: 'div.ace_line .ace_xml:contains("oe_structure")',
            run() {
                ace.edit(document.querySelector("#resource-editor div"))
                    .getSession()
                    .insert({row: 8, column: 1}, '<p>More text</p>\n');
            },
        },
        {
            content: "Save the html editor",
            trigger: ".o_resource_editor button.btn-primary",
            run: "click",
        },
        {
            content: "Close the html editor",
            trigger: ".o_resource_editor button.btn-secondary",
            run: "click",
        },
        {
            content: "Page is updated",
            trigger: ":iframe body:contains(More text)",
        },
    ]
);
