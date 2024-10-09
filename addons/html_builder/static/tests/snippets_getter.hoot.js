import { realOrm } from "@web/../tests/_framework/module_set.hoot";

let websiteSnippets;
export const getWebsiteSnippets = async () => {
    if (!websiteSnippets) {
        websiteSnippets = await realOrm(
            "ir.ui.view",
            "render_public_asset",
            ["website.snippets"],
            {}
        );
    }
    return websiteSnippets;
};
