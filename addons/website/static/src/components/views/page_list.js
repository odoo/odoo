import { _t } from "@web/core/l10n/translation";
import { usePageManager } from "./page_manager_hook";
import {PageSearchModel} from "./page_search_model";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {DeletePageDialog, DuplicatePageDialog} from '@website/components/dialog/page_properties';
import { useService } from "@web/core/utils/hooks";


export class PageListController extends listView.Controller {
    static components = {
        ...listView.Controller.components,
    };

    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.pageManager = usePageManager({
            resModel: this.props.resModel,
            createAction: this.props.context.create_action,
        });
        if (this.props.resModel === "website.page") {
            this.archiveEnabled = false;
        }
    }

    /**
     * @override
     */
    onClickCreate() {
        return this.pageManager.createWebsiteContent();
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
                    pageIds: resIds,
                    onDuplicate: () => {
                        this.model.load();
                    },
                });
            };
        }
        return menuItems;
    }

    async onDeleteSelectedRecords() {
        const pageIds = this.model.root.selection.map((record) => record.resId);
        const newPageTemplateRecords = await this.orm.read("website.page", pageIds, ["is_new_page_template"]);
        this.dialogService.add(DeletePageDialog, {
            resIds: pageIds,
            resModel: this.props.resModel,
            onDelete: () => {
                this.model.root.deleteRecords();
            },
            hasNewPageTemplate: newPageTemplateRecords.some(record => record.is_new_page_template),
        });
    }

    async togglePublished(publish) {
        const resIds = this.model.root.selection.map(record => record.resId);
        await this.orm.write(this.props.resModel, resIds, {is_published: publish});
        this.actionService.switchView('list');
    }
}

export class PageListRenderer extends listView.Renderer {
    static recordRowTemplate = "website.PageListRenderer.RecordRow";
}

export const PageListView = {
    ...listView,
    Renderer: PageListRenderer,
    Controller: PageListController,
    SearchModel: PageSearchModel,
};

registry.category("views").add("website_pages_list", PageListView);
