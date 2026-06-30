import { registry } from "@web/core/registry";

registry
    .category("html_builder.snippetsPreprocessor")
    .add("website_sale_snippets", (namespace, snippets) => {
        if (namespace === "website.snippets") {
            // This should be empty in master, it is used to fix snippets in stable.
            snippets
                .querySelector(".s_dynamic_snippet_category_list .dynamic_snippet_template > *")
                ?.classList.add("s_dialog_preview");
        }
    });
