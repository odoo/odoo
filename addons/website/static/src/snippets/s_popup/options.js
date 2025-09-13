/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

options.registry.SnippetPopup = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        // Note: the link are excluded here so that internal modal buttons do
        // not close the popup as we want to allow edition of those buttons.
        this.$bsTarget.on('click.SnippetPopup', '.js_close_popup:not(a, .btn)', ev => {
            ev.stopPropagation();
            this.onTargetHide();
            this.trigger_up('snippet_option_visibility_update', {show: false});
        });
        this.$bsTarget.on('shown.bs.modal.SnippetPopup', () => {
            this.trigger_up('snippet_option_visibility_update', {show: true});
            // TODO duplicated code from the popup public widget, this should
            // be moved to a *video* public widget and be reviewed in master
            this.$target[0].querySelectorAll('.media_iframe_video').forEach(media => {
                const iframe = media.querySelector('iframe');
                iframe.src = media.dataset.oeExpression || media.dataset.src; // TODO still oeExpression to remove someday
            });
        });
        this.$bsTarget.on('hide.bs.modal.SnippetPopup', () => {
            this.trigger_up('snippet_option_visibility_update', {show: false});
            this._removeIframeSrc();
        });
        // The video might be playing before entering edit mode (possibly with
        // sound). Stop the video, as the user can't do it (no button on video
        // in edit mode).
        this._removeIframeSrc();
        if (!this.$target[0].parentElement.matches("#website_cookies_bar")) {
            this.trigger_up("option_update", {
                optionName: "anchor",
                name: "modalAnchor",
                data: {
                    buttonEl: this._requestUserValueWidgets("onclick_opt")[0].el,
                },
            });
        }
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
        this.$bsTarget.off('.SnippetPopup');
    },
    /**
     * @override
     */
    onBuilt: function () {
        this._assignUniqueID();
        // Fix in stable to convert the data-focus bootstrap option from version 4.0 to
        // 5.1 (renamed to data-bs-focus).
        const popup = this.$target.closest('.s_popup_middle');
        if (popup && popup.attr('data-focus')) {
            popup.attr('data-bs-focus', popup.attr('data-focus'));
            popup[0].removeAttribute('data-focus');
        }
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
        this.options.wysiwyg.odooEditor.observerUnactive();
        this.$bsTarget.modal('show');
        $(this.$target[0].ownerDocument.body).children('.modal-backdrop:last').addClass('d-none');
        this.options.wysiwyg.odooEditor.observerActive();
    },
    /**
     * @override
     */
    onTargetHide: async function () {
        return new Promise(resolve => {
            const timeoutID = setTimeout(() => {
                this.$bsTarget.off('hidden.bs.modal.popup_on_target_hide');
                resolve();
            }, 500);
            this.$bsTarget.one('hidden.bs.modal.popup_on_target_hide', () => {
                clearTimeout(timeoutID);
                resolve();
            });
            // The following line is in charge of hiding .s_popup at the same
            // time the modal is closed when the page is saved in edit mode.
            this.$target[0].closest('.s_popup').classList.add('d-none');
            this.$bsTarget.modal('hide');
        });
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Moves the snippet in #o_shared_blocks to be common to all pages or inside
     * the first editable oe_structure in the main to be on current page only.
     *
     * @see this.selectClass for parameters
     */
    moveBlock: function (previewMode, widgetValue, params) {
        const selector = widgetValue === 'allPages' ?
            '#o_shared_blocks' : 'main .oe_structure:o_editable';
        const whereEl = $(this.$target[0].ownerDocument).find(selector)[0];
        const popupEl = this.$target[0].closest('.s_popup');
        whereEl.prepend(popupEl);
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
                return this.$target[0].closest('#o_shared_blocks') ? 'allPages' : 'currentPage';
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
