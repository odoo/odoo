odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.detail.moduleName === "@web_editor/js/frontend/loadWysiwygFromTextarea") {
        const publicWidget = odoo.loader.modules.get("@web/legacy/js/public/public_widget")[Symbol.for('default')];
        const { loadWysiwygFromTextarea } = e.detail.module;

        publicWidget.registry['public_user_editor_test'] = publicWidget.Widget.extend({
            selector: 'textarea.o_public_user_editor_test_textarea',

            /**
             * @override
             */
            start: async function () {
                await this._super(...arguments);
                await loadWysiwygFromTextarea(this, this.el, {});
            },
        });
    }
})
