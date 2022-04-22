odoo.define('website.s_popup_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');

options.registry.SnippetPopup = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        // Editor jQuery and iFrame jQuery isn't the same instance. This means
        // that events within the iframe (so popup events) aren't handled by
        // the editor's jQuery. To apply and listen to events on the modal,
        // we need to get it from the iframe's jQuery instance.
        this.$iframeTarget = this.$target[0].ownerDocument.defaultView.$(this.$target[0]);
        // Note: the link are excluded here so that internal modal buttons do
        // not close the popup as we want to allow edition of those buttons.
        this.$iframeTarget.on('click.SnippetPopup', '.js_close_popup:not(a, .btn)', ev => {
            ev.stopPropagation();
            this.onTargetHide();
            this.trigger_up('snippet_option_visibility_update', {show: false});
        });
        this.$iframeTarget.on('shown.bs.modal.SnippetPopup', () => {
            this.trigger_up('snippet_option_visibility_update', {show: true});
            // TODO duplicated code from the popup public widget, this should
            // be moved to a *video* public widget and be reviewed in master
            this.$target[0].querySelectorAll('.media_iframe_video').forEach(media => {
                const iframe = media.querySelector('iframe');
                iframe.src = media.dataset.oeExpression || media.dataset.src; // TODO still oeExpression to remove someday
            });
        });
        this.$iframeTarget.on('hidden.bs.modal.SnippetPopup', () => {
            this.trigger_up('snippet_option_visibility_update', {show: false});
            this._removeIframeSrc();
        });
        // The video might be playing before entering edit mode (possibly with
        // sound). Stop the video, as the user can't do it (no button on video
        // in edit mode).
        this._removeIframeSrc();
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        // The video should not start before the modal opens, remove it from the
        // DOM. It will be added back on modal open to start the video.
        this._removeIframeSrc();
        this.$iframeTarget.off('.SnippetPopup');
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
        this.$iframeTarget.modal('show');
        $(this.$target[0].ownerDocument.body).children('.modal-backdrop:last').addClass('d-none');
    },
    /**
     * @override
     */
    onTargetHide: async function () {
        return new Promise(resolve => {
            const timeoutID = setTimeout(() => {
                this.$iframeTarget.off('hidden.bs.modal.popup_on_target_hide');
                resolve();
            }, 500);
            this.$iframeTarget.one('hidden.bs.modal.popup_on_target_hide', () => {
                clearTimeout(timeoutID);
                resolve();
            });
            this.$iframeTarget.modal('hide');
        });
    },
    /**
     * @override
     */
    cleanForSave: function () {
        this.$target.removeClass("s_popup_overflow_page");
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
     * @see this.selectClass for parameters
     */
    setBackdrop(previewMode, widgetValue, params) {
        const color = widgetValue ? 'var(--black-50)' : '';
        this.$target[0].style.setProperty('background-color', color, 'important');
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
    /**
     * Removes the iframe `src` attribute (a copy of the src is already on the
     * parent `oe-expression` attribute).
     *
     * @private
     */
    _removeIframeSrc() {
        this.$target.find('.media_iframe_video iframe').each((i, iframe) => {
            iframe.src = '';
        });
    },
});
});
