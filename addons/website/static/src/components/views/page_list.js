/** @odoo-module **/

import {PageControllerMixin, PageRendererMixin} from "./page_views_mixin";
import {PageSearchModel} from "./page_search_model";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {sprintf} from "@web/core/utils/strings";
import {DeletePageDialog} from '@website/components/dialog/page_properties';


export class PageListController extends PageControllerMixin(listView.Controller) {
    /**
     * @override
     */
    onClickCreate() {
        return this.createWebsiteContent();
    }

    /**
     * Adds a "Publish/Unpublish" button to the 'action' menu of the list view.
     *
     * @override
     */
    getActionMenuItems() {
        const actionMenuItems = super.getActionMenuItems();
        // 'Archive' / 'Unarchive' options are disabled only on 'website.page' list view.
        if (this.props.resModel === 'website.page') {
            actionMenuItems.other = actionMenuItems.other
                .filter(item => !['archive', 'unarchive'].includes(item.key));
        }
        if (this.props.fields.hasOwnProperty('is_published')) {
            actionMenuItems.other.splice(-1, 0, {
                description: this.env._t("Publish"),
                callback: async () => {
                    this.dialogService.add(ConfirmationDialog, {
                        title: this.env._t("Publish Website Content"),
                        body: sprintf(this.env._t("%s record(s) selected, are you sure you want to publish them all?"), this.model.root.selection.length),
                        confirm: () => this.togglePublished(true),
                    });
                }
            },
            {
                description: this.env._t("Unpublish"),
                callback: async () => this.togglePublished(false),
            });
        }
        return actionMenuItems;
    }

    onDeleteSelectedRecords() {
        this.dialogService.add(DeletePageDialog, {
            resIds: this.model.root.selection.map((record) => record.resId),
            resModel: this.props.resModel,
            onDelete: () => {
                this.model.root.deleteRecords();
            },
        });
    }

    async togglePublished(publish) {
        const resIds = this.model.root.selection.map(record => record.resId);
        await this.orm.write(this.props.resModel, resIds, {is_published: publish});
        this.actionService.switchView('list');
    }
}
PageListController.template = `website.PageListView`;

// TODO master: remove `PageRendererMixin` extend and props override
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
    SearchModel: PageSearchModel,
};

registry.category("views").add("website_pages_list", PageListView);
