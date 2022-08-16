/** @odoo-module **/

import ListController from 'web.ListController';
import viewRegistry from 'web.view_registry';
import ListView from 'web.ListView';
import {ComponentWrapper} from 'web.OwlCompatibility';
import {PagePropertiesDialogManager} from '@website/components/dialog/page_properties';
import {qweb} from 'web.core';

const WebsitePageListController = ListController.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    willStart() {
        return Promise.all([this._super(...arguments), this._getRenderContext()]);
    },
    /**
     * @override
     */
    renderButtons($node) {
        this.$buttons = $(qweb.render('PageListView.WebsiteSelect', {
            websites: this.websites,
            active: this._getWebsite(0),
        }));
        this.$buttons.find('.dropdown-item').click(this._onButtonClick.bind(this));
        if ($node) {
            this.$buttons.appendTo($node);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _callButtonAction(attrs, record) {
        switch (attrs.name) {
            case 'action_optimize_seo':
                this._goToPage(record.data.url, record.data.website_id.res_id, {
                    enable_seo: true,
                });
                break;
            case 'action_manage_page':
                await this._addDialog(record);
                break;
            case 'action_clone_page':
                await this._addDialog(record, 'clone');
                break;
            case 'action_delete_page':
                await this._addDialog(record, 'delete');
                break;
            case 'action_edit_page':
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'ir.ui.view',
                    res_id: record.data.view_id.res_id,
                    views: [[false, 'form']],
                });
                break;
            default:
                return this._super(...arguments);
        }
    },
    /**
     * @private
     */
    _goToPage(path, website, options = {}) {
        this.do_action('website.website_preview', {
            additional_context: {
                params: {
                    path: path,
                    website_id: website || '',
                    ...options,
                }
            },
        });
    },
    /**
     * @private
     */
    async _addDialog(record, mode = '') {
        this._pagePropertiesDialog = new ComponentWrapper(this, PagePropertiesDialogManager, {
            resId: record.data.id,
            onClose: this._onCloseDialog.bind(this),
            onRecordSaved: this.reload.bind(this),
            mode: mode,
        });
        await this._pagePropertiesDialog.mount(this.el);
    },
    /**
     * Removes page properties wrapper when dialog is closed.
     *
     * @private
     */
    _onCloseDialog() {
        if (this._pagePropertiesDialog) {
            this._pagePropertiesDialog.destroy();
        }
        this._pagePropertiesDialog = undefined;
    },
    /**
     * @private
     */
    _getRenderContext() {
        return this._rpc({
            model: 'website',
            method: 'search_read',
            fields: ['id', 'name'],
        }).then((result) => {
            this.websites = [{id: 0, name: 'All Websites'}, ...result];
        });
    },
    /**
     * @private
     */
    _getWebsite(id) {
        return this.websites.find(website => website.id === id);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onOpenRecord(event) {
        const record = this.model.get(event.data.id, {raw: true});
        this._goToPage(record.data.url, record.data.website_id);
    },
    _onButtonClick: async function (event) {
        const activeWebsite = this._getWebsite(parseInt(event.target.dataset.websiteId));
        this.$buttons[0].querySelector('.o_website_active').textContent = activeWebsite.name;
        this.reload({
            domain: activeWebsite.id ? [['website_id', '=', activeWebsite.id]] : [],
        });
    }
});

const WebsitePageListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: WebsitePageListController,
    }),
});

viewRegistry.add('website_page_list', WebsitePageListView);

export default {
    WebsitePageListController: WebsitePageListController,
    WebsitePageListView: WebsitePageListView,
};
