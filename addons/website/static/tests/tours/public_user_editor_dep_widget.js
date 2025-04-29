// @odoo-module ignore

odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.detail.moduleName === "@web_editor/js/frontend/loadWysiwygFromTextarea") {
        const { Interaction } = odoo.loader.modules.get("@web/public/interaction");
        const { registry } = odoo.loader.modules.get("@web/core/registry");
        const { loadWysiwygFromTextarea } = e.detail.module;

        class PublicUserEditorTest extends Interaction {
            static selector = "textarea.o_public_user_editor_test_textarea";

            /**
             * @override
             */
            async start() {
                await loadWysiwygFromTextarea(this, this.el, {});
            }
        }

        registry
            .category("public.interactions")
            .add("website.public_user_editor_test", PublicUserEditorTest);
    }
});
