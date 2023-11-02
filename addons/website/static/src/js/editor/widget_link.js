/** @odoo-module **/

import { LinkTools } from '@web_editor/js/wysiwyg/widgets/link_tools';
import { patch } from "@web/core/utils/patch";

import { onWillStart, status, useEffect } from '@odoo/owl';
import wUtils from "@website/js/utils";
import { debounce } from "@web/core/utils/timing";

const LINK_DEBOUNCE = 1000;

patch(LinkTools.prototype, {
    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    async start() {
        var def = await super.start(...arguments);
        this._adaptPageAnchor();
        return def;
    },

    setup() {
        super.setup();
        onWillStart(() => {
            this._adaptPageAnchor = debounce(this._adaptPageAnchor, LINK_DEBOUNCE);
        });
        useEffect((container) => {
            const input = container?.querySelector(`input[name="url"]`);
            if (!input) {
                return;
            }
            const options = {
                classes: {
                    "ui-autocomplete": 'o_website_ui_autocomplete'
                },
                body: this.$editable[0].ownerDocument.body,
                urlChosen: this._onAutocompleteClose.bind(this),
                isDestroyed: () => status(this) === 'destroyed',
            };
            const unmountAutocompleteWithPages = wUtils.autocompleteWithPages(input, options);
            return () => unmountAutocompleteWithPages();
            }, () => [this.linkComponentWrapperRef.el]);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptPageAnchor() {
        const urlInputValue = this.$el.find('input[name="url"]').val();
        const $pageAnchor = this.$el.find('.o_link_dialog_page_anchor');
        const isFromWebsite = urlInputValue[0] === '/';
        const $selectMenu = this.$el.find('we-selection-items[name="link_anchor"]');

        if ($selectMenu.data("anchor-for") !== urlInputValue) { // avoid useless query
            $pageAnchor.toggleClass('d-none', !isFromWebsite);
            $selectMenu.empty();
            const always = () => {
                const anchor = `#${urlInputValue.split('#')[1]}`;
                let weTogglerText = '\u00A0';
                if (anchor) {
                    const weButtonEls = $selectMenu[0].querySelectorAll('we-button');
                    if (Array.from(weButtonEls).some(el => el.textContent === anchor)) {
                        weTogglerText = anchor;
                    }
                }
                $pageAnchor[0].querySelector('we-toggler').textContent = weTogglerText;
            };
            const urlWithoutHash = urlInputValue.split("#")[0];
            wUtils.loadAnchors(urlWithoutHash, this.$editable[0].ownerDocument.body).then(anchors => {
                for (const anchor of anchors) {
                    const $option = $('<we-button class="dropdown-item">');
                    $option.text(anchor);
                    $option.data('value', anchor);
                    $selectMenu.append($option);
                }
            }).finally(always);
        }
        $selectMenu.data("anchor-for", urlInputValue);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAutocompleteClose() {
        this.__onURLInput();
    },
    /**
     * @override
     */
    _onURLInput() {
        super._onURLInput(...arguments);
        this._adaptPageAnchor();
    },
    /**
     * @override
     * @param {Event} ev
     */
    _onPickSelectOption(ev) {
        if (ev.currentTarget.closest('[name="link_anchor"]')) {
            const anchorValue = $(ev.currentTarget).data('value');
            const $urlInput = this.$el.find('[name="url"]');
            let urlInputValue = $urlInput.val();
            if (urlInputValue.indexOf('#') > -1) {
                urlInputValue = urlInputValue.substr(0, urlInputValue.indexOf('#'));
            }
            $urlInput.val(urlInputValue + anchorValue);
            // Updates the link in the DOM with the chosen anchor.
            this.__onURLInput();
        }
        super._onPickSelectOption(...arguments);
    },
});
