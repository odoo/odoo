/** @odoo-module **/

import {PageControllerMixin, PageRendererMixin} from "./page_views_mixin";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';


export class PageListController extends PageControllerMixin(listView.Controller) {
    /**
     * @override
     */
    onClickCreate() {
        return this.createWebsiteContent();
    }
}
PageListController.template = `website.PageListView`;

export class PageListRenderer extends PageRendererMixin(listView.Renderer) {}
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
