/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';

options.registry.NewsletterLayout = options.registry.SelectTemplate.extend({
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.containerSelector = '> .container, > .container-fluid, > .o_container_small';
        this.selectTemplateWidgetName = 'newsletter_template_opt';
    },

    /**
     * @override
     */
    async selectTemplate(previewMode) {
        const _super = this._super.bind(this);
        await this._templatesLoading;
        if (previewMode !== "reset" && !this.beforePreviewNodes && this._currentTemplate) {
            this._templates[this._currentTemplate] = this.containerEl.innerHTML;
        }
        return _super(...arguments);
    },
    /**
     * @override
     */
    _onWidgetOpening(ev) {
        this._super(...arguments);
        if (ev.target.getName() === this.selectTemplateWidgetName) {
            this._currentTemplate = ev.target.getValue("selectTemplate");
        }
    },
});
