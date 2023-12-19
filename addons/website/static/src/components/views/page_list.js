/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import {PageControllerMixin, PageRendererMixin} from "./page_views_mixin";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {useService} from "@web/core/utils/hooks";
import {DeletePageDialog, DuplicatePageDialog} from '@website/components/dialog/page_properties';
import {CheckboxItem} from "@web/core/dropdown/checkbox_item";


export class PageListController extends PageControllerMixin(listView.Controller) {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService('orm');
        if (this.props.resModel === "website.page") {
            this.archiveEnabled = false;
        }
    }

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
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        if (this.props.fields.hasOwnProperty('is_published')) {
            menuItems.publish = {
                sequence: 15,
                icon: "fa fa-globe",
                description: _t("Publish"),
                callback: async () => {
                    this.dialogService.add(ConfirmationDialog, {
                        title: _t("Publish Website Content"),
                        body: _t("%s record(s) selected, are you sure you want to publish them all?", this.model.root.selection.length),
                        confirm: () => this.togglePublished(true),
                    });
                },
            };
            menuItems.unpublish = {
                sequence: 16,
                icon: "fa fa-chain-broken",
                description: _t("Unpublish"),
                callback: async () => this.togglePublished(false),
            };
        }
        if (this.props.resModel === "website.page") {
            menuItems.duplicate.callback = async (records = []) => {
                const resIds = this.model.root.selection.map((record) => record.resId);
                this.dialog.add(DuplicatePageDialog, {
                    // TODO Remove pageId in master
                    pageId: 0, // Ignored but mandatory
                    pageIds: resIds,
                    onDuplicate: () => {
                        this.model.load();
                    },
                });
            };
        }
        return menuItems;
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
PageListController.components = {
    ...listView.Controller.components,
    CheckboxItem,
};

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
