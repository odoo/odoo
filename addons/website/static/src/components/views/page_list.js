/** @odoo-module **/

import {AddPageDialog} from "../dialog/dialog";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {useService} from "@web/core/utils/hooks";
import { csrf_token } from 'web.core';

const {onWillStart, useState} = owl;


export class PageListController extends listView.Controller {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.website = useService('website');
        this.http = useService('http');

        this.websiteSelection = [{id: 0, name: this.env._t("All Websites")}];

        this.state = useState({
            activeWebsite: this.websiteSelection[0],
        });

        onWillStart(async () => {
            await this.website.fetchWebsites();
            this.websiteSelection.push(...this.website.websites);
        });
    }

    /**
     * @override
     */
    onClickCreate() {
        if (this.props.resModel === 'website.page') {
            return this.dialogService.add(AddPageDialog, {
                addPage: async (name, addMenu) => {
                    // TODO this is duplicated code from new_content.js, this
                    // should be shared somehow.
                    // FIXME this always create on website 1 whatever we do.
                    const url = `/website/add/${encodeURIComponent(name)}`;
                    const data = await this.http.post(url, { 'add_menu': addMenu || '', csrf_token });
                    if (data.view_id) {
                        this.actionService.doAction({
                            'res_model': 'ir.ui.view',
                            'res_id': data.view_id,
                            'views': [[false, 'form']],
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                        });
                    } else {
                        this.website.goToWebsite({ path: data.url, edition: true });
                    }
                },
            });
        }
        const action = this.props.context.create_action;
        if (action) {
            if (/^\//.test(action)) {
                window.location.replace(action);
                return;
            }
            this.actionService.doAction(action, {
                onClose: (data) => {
                    if (data) {
                        this.website.goToWebsite({path: data.path});
                    }
                },
            });
        }
    }

    onSelectWebsite(website) {
        this.state.activeWebsite = website;
    }
}
PageListController.template = `website.PageListView`;

export class PageListRenderer extends listView.Renderer {
    /**
     * The goal here is to tweak the renderer to display pages following some
     * rules:
     * - All websites (props.activeWebsite.id === 0):
     *     -> Show all generic/specific pages.
     * - A website is selected:
     *     -> Display website-specific pages & generic ones (only those without
     *        specific clones).
     */
    pageFilter(record, records) {
        return !this.props.activeWebsite.id
            || this.props.activeWebsite.id === record.data.website_id[0]
            || !record.data.website_id[0] && records.filter(rec => rec.data.url === record.data.url).length === 1;
    }
}
PageListRenderer.props = [
    ...listView.Renderer.props,
    "activeWebsite",
];
PageListRenderer.recordRowTemplate = "website.PageListRenderer.RecordRow";

export const PageListView = {
    ...listView,
    Renderer: PageListRenderer,
    Controller: PageListController,
};

registry.category("views").add("website_pages_list", PageListView);
