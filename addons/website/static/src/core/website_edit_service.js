import { registry } from "@web/core/registry";

registry.category("services").add("website_edit", {
    dependencies: ["website_core"],
    start(env, { website_core }) {
        function isEditingTranslations() {
            return !!website_core.el.closest("html").dataset.edit_translations;
        }

        return { isEditingTranslations };
    },
});
