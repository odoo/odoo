import options from "@web_editor/js/editor/snippets.options";

options.registry.MegaMenuLayout = options.registry.MegaMenuLayout.extend({
    /**
     * @override
     */
    events: {
        'click .fetch_ecom_categories': '_onClick',
    },

    _onClick() {
        const selectedButton = document.querySelector('.mega_menu_template we-button.active');
        if (!selectedButton) return;

        const currentTemplateId = selectedButton.getAttribute('data-select-template');
        const newTemplateId = this._getNewTemplateId(currentTemplateId);

        if (newTemplateId) {
            this._switchTemplate(newTemplateId);
        }
    },

    _getNewTemplateId(currentTemplateId) {
        return currentTemplateId.startsWith('website.')
            ? currentTemplateId.replace('website.', 'website_sale.')
            : null;
    },

    _switchTemplate(newTemplateId) {
        this._getTemplate(newTemplateId)
            .then(template => {
                const sectionEl = this.containerEl.querySelector('section');
                if (sectionEl) {
                    sectionEl.outerHTML = template;
                }
            })
            .catch(error => console.error('Error switching template:', error));
    },
});
