/** @odoo-module **/

import { LinkTools } from '@web_editor/js/wysiwyg/widgets/link_tools';
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

import {status} from '@odoo/owl';
import wUtils from "@website/js/utils";
import { debounce } from "@web/core/utils/timing";

const LINK_DEBOUNCE = 1000;

patch(LinkTools.prototype, {
    setup() {
        this.rpc = useService('rpc');
        return super.setup(...arguments);
    },
    /**
     *
     * @override
     */
    onWillStart() {
        this._adaptPageAnchor = debounce(this._adaptPageAnchor, LINK_DEBOUNCE);
        return super.onWillStart(...arguments);
    },
    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    async start() {
        var def = await super.start(...arguments);
        const options = {
            position: {
                collision: 'flip flipfit',
            },
            classes: {
                "ui-autocomplete": 'o_website_ui_autocomplete'
            },
            body: this.$editable[0].ownerDocument.body,
            urlChosen: this._onAutocompleteClose.bind(this),
            isDestroyed: () => status(this) === 'destroyed',
        };
        wUtils.autocompleteWithPages(this.rpc.bind(this), this.$el.find('input[name="url"]'), options);
        this._adaptPageAnchor();
        return def;
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
                always();
            }).guardedCatch(always);
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
        this._onURLInput();
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
        }
        super._onPickSelectOption(...arguments);
    },
});
