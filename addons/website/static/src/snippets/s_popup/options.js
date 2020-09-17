odoo.define('website.s_popup_options', function (require) {
'use strict';

const snippetOptions = require('web_editor.snippets.options');

snippetOptions.registry.SnippetPopup = snippetOptions.SnippetOptionWidget.extend({
    /**
     * @override
     */
    start: function () {
        // Note: the link are excluded here so that internal modal buttons do
        // not close the popup as we want to allow edition of those buttons.
        this.trigger_up('snippet_option_visibility_update', {show: false});
        this.$target.on('click.SnippetPopup', '.js_close_popup:not(a, .btn)', ev => {
            ev.stopPropagation();
            this.onTargetHide();
            this.trigger_up('snippet_option_visibility_update', {show: false});
        });
        this.$target.on('shown.bs.modal.SnippetPopup', () => {
            this.trigger_up('snippet_option_visibility_update', {show: true});
        });
        this.$target.on('hidden.bs.modal.SnippetPopup', () => {
            this.trigger_up('snippet_option_visibility_update', {show: false});
        });
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        this.$target.off('.SnippetPopup');
    },
    /**
     * @override
     */
    onBuilt: function () {
        this._assignUniqueID();
    },
    /**
     * @override
     */
    onClone: function () {
        this._assignUniqueID();
    },
    /**
     * @override
     */
    onTargetShow: async function () {
        this.$target.modal('show');
        $(document.body).children('.modal-backdrop:last').addClass('d-none');
    },
    /**
     * @override
     */
    onTargetHide: async function (previewMode) {
        await new Promise((resolve) => {
            const timeoutID = setTimeout(() => {
                this.$target.off('hidden.bs.modal.popup_on_target_hide');
                resolve();
            }, 500);
            this.$target.one('hidden.bs.modal.popup_on_target_hide', () => {
                clearTimeout(timeoutID);
                resolve();
            });
            this.$target.modal('hide');
        });
        await this._refreshTarget();
    },
    /**
     * @override
     */
    cleanForSave: async function() {
        await this.onTargetHide();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Moves the snippet in footer to be common to all pages
     * or inside wrap to be on one page only
     *
     * @see this.selectClass for parameters
     */
    moveBlock: async function (previewMode, widgetValue, params) {
        const $container = $(widgetValue === 'moveToFooter' ? 'footer' : 'main');
        this.$target.closest('.s_popup').prependTo($container.find('.oe_structure:o_editable').first());
        if (previewMode === false) {
            await this.editorHelpers.prepend(this.wysiwyg.editor, $container.find('.oe_structure:o_editable').first()[0], this.$target.closest('.s_popup')[0])
        }

    },
    /**
     * @see this.selectClass for parameters
     */
    async setBackdrop(previewMode, widgetValue, params) {
        const color = widgetValue ? 'var(--black-50)' : '';
        this.$target[0].style.setProperty('background-color', color, 'important');

        if (previewMode === false) await this._refreshTarget();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates a unique ID.
     *
     * @private
     */
    _assignUniqueID: function () {
        this.$target.closest('.s_popup').attr('id', 'sPopup' + Date.now());
    },
    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'moveBlock':
                return this.$target.closest('footer').length ? 'moveToFooter' : 'moveToBody';
        }
        return this._super(...arguments);
    },
});
});
