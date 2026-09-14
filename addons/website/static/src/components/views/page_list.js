/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { ConfirmationDialog } from "@web/ui/dialog";
import { listView } from "@web/views/list";
import {
    DeletePageDialog,
    DuplicatePageDialog,
} from "@website/components/dialog/page_properties";

import { usePageManager } from "./page_manager_hook.js";
import { PageSearchModel } from "./page_search_model.js";

const log = makeLogger("website.view.page_list");

export class PageListController extends listView.Controller {
    static components = {
        ...listView.Controller.components,
    };

    /**
     * @override
     */
    setup() {
        super.setup();
        useLifecycleLog(log);
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.pageManager = usePageManager({
            resModel: this.props.resModel,
            createAction: this.props.context.create_action,
        });
        if (this.props.resModel === "website.page") {
            log.logic("PageListController website.page: archive disabled");
            this.archiveEnabled = false;
        }
    }

    /**
     * @override
     */
    onClickCreate() {
        log.logic("onClickCreate", () => ({ resModel: this.props.resModel }));
        return this.pageManager.createWebsiteContent();
    }

    /**
     * @override
     */
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        if (Object.prototype.hasOwnProperty.call(this.props.fields, "is_published")) {
            menuItems.publish = {
                groupNumber: COG_GROUP.RECORD,
                sequence: 35,
                icon: "fa-solid fa-earth-americas",
                description: _t("Publish"),
                callback: async () => {
                    log.lifecycle("publish confirmation dialog", () => ({
                        selected: this.model.root.selection.length,
                    }));
                    this.dialogService.add(ConfirmationDialog, {
                        title: _t("Publish Website Content"),
                        body: _t(
                            "%s record(s) selected, are you sure you want to publish them all?",
                            this.model.root.selection.length,
                        ),
                        confirm: () => this.togglePublished(true),
                    });
                },
            };
            menuItems.unpublish = {
                groupNumber: COG_GROUP.RECORD,
                sequence: 36,
                icon: "fa-solid fa-link-slash",
                description: _t("Unpublish"),
                callback: async () => this.togglePublished(false),
            };
        }
        if (this.props.resModel === "website.page") {
            menuItems.duplicate.callback = async (records = []) => {
                const resIds = this.model.root.selection.map((record) => record.resId);
                log.logic("duplicate pages", { resIds });
                this.dialog.add(DuplicatePageDialog, {
                    pageIds: resIds,
                    onDuplicate: () => {
                        this.env.searchModel.refreshFilterForAllWebsites();
                    },
                });
            };
        }
        return menuItems;
    }

    async onDeleteSelectedRecords() {
        const pageIds = this.model.root.selection.map((record) => record.resId);
        const endRead = log.perf("onDeleteSelectedRecords read is_new_page_template", {
            pageIds,
        });
        const newPageTemplateRecords = await this.orm.read("website.page", pageIds, [
            "is_new_page_template",
        ]);
        endRead();
        this.dialogService.add(DeletePageDialog, {
            resIds: pageIds,
            resModel: this.props.resModel,
            onDelete: () => {
                log.pipeline("delete selected records", { pageIds });
                this.model.root.deleteRecords();
            },
            hasNewPageTemplate: newPageTemplateRecords.some(
                (record) => record.is_new_page_template,
            ),
        });
    }

    async togglePublished(publish) {
        const resIds = this.model.root.selection.map((record) => record.resId);
        const endWrite = log.perf("togglePublished write", { publish, resIds });
        await this.orm.write(this.props.resModel, resIds, { is_published: publish });
        endWrite();
        this.actionService.switchView("list");
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
