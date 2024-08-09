/** @odoo-module **/

// Import value made visible by _pregenerate_assets_bundles
import { __test__allTemplates } from "@web/core/templates";
import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_compile_owl_templates",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Compile all website-related Owl templates",
            trigger: ":iframe #wrap",
            run: () => {
                if (!__test__allTemplates) {
                    console.error("Templates are not available");
                }
                const app = odoo.__WOWL_DEBUG__.root.__owl__.app;
                const templateNames = Object.keys(__test__allTemplates).filter((name) =>
                    name.includes("website")
                );
                console.log(`Compiling ${templateNames.length} Owl templates.`);
                for (const name of templateNames) {
                    try {
                        app.getTemplate(name);
                    } catch (e) {
                        console.error("Issue in template", name);
                        console.error(e);
                    }
                }
            },
        },
    ]
);
