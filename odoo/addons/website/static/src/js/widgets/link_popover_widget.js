/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

import { LinkPopoverWidget } from '@web_editor/js/wysiwyg/widgets/link_popover_widget';



patch(LinkPopoverWidget.prototype, {
    /**
     * @override
     */
    start() {
        // hide popover while typing on mega menu
        if (this.target.closest('.o_mega_menu')) {
            let timeoutID = undefined;
            this.$target.on('keydown.link_popover', () => {
                this.$target.popover('hide');
                clearTimeout(timeoutID);
                timeoutID = setTimeout(() => this.$target.popover('show'), 1500);
            });
        }
        this.$el.on('click', '.o_we_full_url, .o_we_url_link', this._onPreviewLinkClick.bind(this));

        return super.start(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens website page links in backend mode by forcing the '/@/' controller.
     *
     * @private
     * @param {Event} ev
     */
    async _onPreviewLinkClick(ev) {
        if (this.target.href) {
            const currentUrl = new URL(this.target.href);
            if (window.location.hostname === currentUrl.hostname && !currentUrl.pathname.startsWith('/@/')) {
                ev.preventDefault();
                currentUrl.pathname = `/@${currentUrl.pathname}`;
                browser.open(currentUrl);
            }
        }
    }
});

export class NavbarLinkPopoverWidget extends LinkPopoverWidget {
    constructor(params) {
        super(...arguments);
        this.checkIsWebsiteDesigner = params.checkIsWebsiteDesigner;
        this.onEditLinkClick = params.onEditLinkClick;
        this.onEditMenuClick = params.onEditMenuClick;
    }
    /**
     *
     * @override
     */
    async start() {
        this.isWebsiteDesigner = await this.checkIsWebsiteDesigner();
        const $removeLink = this.$el.find('.o_we_remove_link');
        // remove link has no sense on navbar menu links, instead show edit menu
        if (this.isWebsiteDesigner) {
            const $anchor = $('<a/>', {
                href: '#', class: 'ms-2 js_edit_menu', title: _t('Edit Menu'),
                'data-bs-placement': 'top', 'data-bs-toggle': 'tooltip',
            }).append($('<i/>', {class: 'fa fa-sitemap'}));
            $removeLink.replaceWith($anchor);
            $anchor.on('click', () => this.onEditMenuClick(this));
        } else {
            this.$el.find('.o_we_edit_link').remove();
            $removeLink.remove();
        }

        return super.start(...arguments);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the menu item editor.
     *
     * @override
     * @param {Event} ev
     */
    _onEditLinkClick(ev) {
        this.onEditLinkClick(this);
    }
}
