import { registry } from "@web/core/registry";

function pressAltA() {
    return {
        content: "Press Alt+a",
        trigger: "body",
        run: "press Alt+a",
        expectUnloadPage: true,
    };
}

function searchParamsCheck() {
    return {
        content: "Check URL does not contain edit_translations or enable_editor",
        trigger: "body",
        run: () => {
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has("edit_translations") || urlParams.has("enable_editor")) {
                throw new Error(
                    "URL should not contain edit_translations or enable_editor after reload"
                );
            }
        },
    };
}

registry.category("web_tour.tours").add("alt_a_edit", {
    url: "/",
    steps: () => [
        pressAltA(),
        {
            content: "Check that the sidebar is in edit mode",
            trigger: ".o_builder_sidebar_open .o-tab-content #snippet_groups",
        },
        {
            content: "Check that the iframe is in edit mode",
            trigger:
                ":iframe html[data-editable='1']:not([data-translatable='1'][data-edit_translations='1'])",
        },
        searchParamsCheck(),
    ],
});

registry.category("web_tour.tours").add("alt_a_translation", {
    url: "/fr",
    steps: () => [
        pressAltA(),
        {
            content: "Check that the sidebar is in translate mode",
            trigger:
                ".o_builder_sidebar_open .o-tab-content .options-container-header:contains(Translation)",
        },
        {
            content: "Check that the iframe is in translate mode",
            trigger:
                ":iframe html[data-translatable='1'][data-edit_translations='1']:not([data-editable='1'])",
        },
        searchParamsCheck(),
    ],
});
