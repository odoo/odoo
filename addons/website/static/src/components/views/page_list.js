/** @odoo-module **/

import {AddPageDialog} from "../dialog/dialog";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {useService} from "@web/core/utils/hooks";

const {onWillStart, useState} = owl;


export class PageListController extends listView.Controller {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.website = useService('website');

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
            return this.dialogService.add(AddPageDialog, {selectWebsite: true});
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
     * The goal here is to tweak the renderer to display records following some
     * rules:
     * - All websites (props.activeWebsite.id === 0):
     *     -> Show all generic/specific records.
     * - A website is selected:
     *     -> Display website-specific records & generic ones (only those without
     *        specific clones).
     */
    recordFilter(record, records) {
        return !this.props.activeWebsite.id
            || this.props.activeWebsite.id === record.data.website_id[0]
            || !record.data.website_id[0] && records.filter(rec => rec.data.website_url === record.data.website_url).length === 1;
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
