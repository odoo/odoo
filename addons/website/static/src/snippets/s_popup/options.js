odoo.define('website.s_popup_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');

options.registry.SnippetPopup = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        this.$target.find('.s_popup_close').on('click', () => {
            this.onTargetHide();
            this.trigger_up('snippet_option_visibility_update', {show: false});
        });
        return this._super(...arguments);
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
        this.$target.removeClass('d-none');
    },
    /**
     * @override
     */
    onTargetHide: async function () {
        this.$target.addClass('d-none');
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
    moveBlock: function (previewMode, widgetValue, params) {
        const $container = $(widgetValue === 'moveToFooter' ? 'footer' : 'main');
        this.$target.closest('.s_popup').prependTo($container.find('.oe_structure:o_editable').first());
    },
    /**
     * Switch layout from modal <--> a sticky div
     *
     * @see this.selectClass for parameters
     */
    setLayout: function (previewMode, widgetValue, params) {
        const isModal = widgetValue === 'modal';
        this.$target.toggleClass('s_popup_fixed', !isModal);
        this.$target.toggleClass('s_popup_center modal', isModal);
        this.$target.find('.s_popup_frame').toggleClass('modal-dialog modal-dialog-centered', isModal);
        this.$target.find('.s_popup_content').toggleClass('modal-content', isModal);
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
            case 'setLayout':
                return this.$target.hasClass('s_popup_center') ? 'modal' : 'fixed';
        }
        return this._super(...arguments);
    },
});
});
