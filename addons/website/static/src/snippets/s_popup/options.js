import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";

export class SnippetPopup extends SnippetOption {
    constructor({ callbacks }) {
        super(...arguments);
        this.$bsTarget = this.ownerDocument.defaultView.$(this.$target[0]);
        this.website = this.env.services.website;
        this.notifyOptions = callbacks.notifyOptions;
        this.updateSnippetOptionVisibility = callbacks.updateSnippetOptionVisibility;
    }
    /**
     * @override
     */
    async willStart() {
        await super.willStart();

        // Note: the link are excluded here so that internal modal buttons do
        // not close the popup as we want to allow edition of those buttons.
        this.$bsTarget.on('click.SnippetPopup', '.js_close_popup:not(a, .btn)', ev => {
            ev.stopPropagation();
            this.onTargetHide();
            this.updateSnippetOptionVisibility(false);
        });
        this.$bsTarget.on('shown.bs.modal.SnippetPopup', () => {
            this.updateSnippetOptionVisibility(true);
            // TODO duplicated code from the popup public widget, this should
            // be moved to a *video* public widget and be reviewed in master
            this.$target[0].querySelectorAll('.media_iframe_video').forEach(media => {
                const iframe = media.querySelector('iframe');
                iframe.src = media.dataset.oeExpression || media.dataset.src; // TODO still oeExpression to remove someday
            });
        });
        this.$bsTarget.on('hide.bs.modal.SnippetPopup', () => {
            this.updateSnippetOptionVisibility(false);
            this._removeIframeSrc();
        });
        // The video might be playing before entering edit mode (possibly with
        // sound). Stop the video, as the user can't do it (no button on video
        // in edit mode).
        this._removeIframeSrc();
    }
    /**
     * @override
     */
    async onRemove() {
        await super.onRemove();
        // The video should not start before the modal opens, remove it from the
        // DOM. It will be added back on modal open to start the video.
        this._removeIframeSrc();
        this.$bsTarget.off('.SnippetPopup');
    }
    /**
     * @override
     */
    async onBuilt() {
        this._assignUniqueID();
        // Fix in stable to convert the data-focus bootstrap option from version 4.0 to
        // 5.1 (renamed to data-bs-focus).
        const popup = this.$target.closest('.s_popup_middle');
        if (popup && popup.attr('data-focus')) {
            popup.attr('data-bs-focus', popup.attr('data-focus'));
            popup[0].removeAttribute('data-focus');
        }
    }
    /**
     * @override
     */
    onClone() {
        this._assignUniqueID();
    }
    /**
     * @override
     */
    async onTargetShow() {
        this.$bsTarget.modal('show');
        $(this.$target[0].ownerDocument.body).children('.modal-backdrop:last').addClass('d-none');
    }
    /**
     * @override
     */
    async onTargetHide() {
        await new Promise(resolve => {
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
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await super.selectDataAttribute(...arguments);
        if (!previewMode && params.attributeName === "display" && widgetValue === "onClick") {
            this.notifyOptions({
                optionName: "Anchor",
                name: "modalAnchor",
            });
        }
    }
    /**
     * Moves the snippet in #o_shared_blocks to be common to all pages or inside
     * the first editable oe_structure in the main to be on current page only.
     *
     * @see this.selectClass for parameters
     */
    moveBlock(previewMode, widgetValue, params) {
        const selector = widgetValue === 'allPages' ?
            '#o_shared_blocks' : 'main .oe_structure:o_editable';
        const whereEl = $(this.$target[0].ownerDocument).find(selector)[0];
        const popupEl = this.$target[0].closest('.s_popup');
        whereEl.prepend(popupEl);
    }
    /**
     * @see this.selectClass for parameters
     */
    setBackdrop(previewMode, widgetValue, params) {
        const color = widgetValue ? 'var(--black-50)' : '';
        this.$target[0].style.setProperty('background-color', color, 'important');
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates a unique ID.
     *
     * @private
     */
    _assignUniqueID() {
        this.$target.closest('.s_popup').attr('id', 'sPopup' + Date.now());
    }
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'moveBlock':
                return this.$target[0].closest('#o_shared_blocks') ? 'allPages' : 'currentPage';
        }
        return super._computeWidgetState(...arguments);
    }
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
    }
}

registerWebsiteOption("SnippetPopup", {
    Class: SnippetPopup,
    template: "website.s_popup_options",
    selector: ".s_popup",
    exclude: "#website_cookies_bar",
    target: ".modal",
    // TODO: Should this be a snippet addition selector? (see
    //  registerSnippetAdditionSelector)
    dropIn: ":not(p).oe_structure:not(.oe_structure_solo):not([data-snippet] *), :not(.o_mega_menu):not(p)[data-oe-type=html]:not([data-snippet] *)",
});

registerWebsiteOption("SnippetPopupCookieBar", {
    Class: SnippetPopup,
    template: "website.s_popup_cookie_bar_options",
    selector: ".s_popup#website_cookies_bar",
    target: ".modal",
});
