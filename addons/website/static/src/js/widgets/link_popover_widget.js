/** @odoo-module **/

import weWidgets from 'wysiwyg.widgets';
import {_t} from 'web.core';
weWidgets.LinkPopoverWidget.include({
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

        return this._super(...arguments);
    },
});

const NavbarLinkPopoverWidget = weWidgets.LinkPopoverWidget.extend({
    events: _.extend({}, weWidgets.LinkPopoverWidget.prototype.events, {
        'click .js_edit_menu': '_onEditMenuClick',
    }),
    /**
     *
     * @override
     */
    start() {
        // remove link has no sense on navbar menu links, instead show edit menu
        const $anchor = $('<a/>', {
            href: '#', class: 'ms-2 js_edit_menu', title: _t('Edit Menu'),
            'data-bs-placement': 'top', 'data-bs-toggle': 'tooltip',
        }).append($('<i/>', {class: 'fa fa-sitemap'}));
        this.$('.o_we_remove_link').replaceWith($anchor);
        return this._super(...arguments);
    },

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
        var self = this;
        var $menu = this.$target.find('[data-oe-id]');
        this.trigger_up('menu_dialog', {
            name: $menu.text(),
            url: $menu.parent().attr('href'),
            save: (name, url) => {
                let websiteId;
                this.trigger_up('context_get', {
                    callback: ctx => websiteId = ctx['website_id'],
                });
                const data = {
                    id: $menu.data('oe-id'),
                    name,
                    url,
                };
                return this._rpc({
                    model: 'website.menu',
                    method: 'save',
                    args: [websiteId, {'data': [data]}],
                }).then(function () {
                    self.options.wysiwyg.odooEditor.observerUnactive();
                    self.$target.attr('href', url);
                    $menu.text(name);
                    self.options.wysiwyg.odooEditor.observerActive();
                });
            },
        });
    },
    /**
     * Opens the menu tree editor. On menu editor save, current page changes
     * will also be saved.
     *
     * @private
     * @param {Event} ev
     */
     _onEditMenuClick(ev) {
        const contentMenu = this.target.closest('[data-content_menu_id]');
        const rootID = contentMenu ? parseInt(contentMenu.dataset.content_menu_id, 10) : undefined;
        this.trigger_up('action_demand', {
            actionName: 'edit_menu',
            params: [rootID],
        });
    },
});

// Exact same static method but instantiating the specialized class.
NavbarLinkPopoverWidget.createFor = weWidgets.LinkPopoverWidget.createFor;

export default NavbarLinkPopoverWidget;
