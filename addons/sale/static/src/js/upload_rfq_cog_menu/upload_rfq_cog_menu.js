/** @odoo-module native */
import { DocumentFileUploader } from "@account/components/document_file_uploader/document_file_uploader";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { COG_GROUP, isActWindowView } from "@web/search/cog_menu/cog_menu_group";

const cogMenuRegistry = registry.category("cogMenu");

export class QuotationRequestUploader extends DocumentFileUploader {
    static template = "upload_rfq_cog_menu.QuotationRequestUploader";

    getResModel() {
        return "sale.order";
    }
}

export const quotationUploaderMenuItem = {
    Component: QuotationRequestUploader,
    groupNumber: COG_GROUP.DATA,
    isDisplayed: (env) =>
        env.searchModel.resModel === "sale.order" &&
        isActWindowView(env, ["list", "kanban"]) &&
        exprToBoolean(env.config.viewArch.getAttribute("create"), true),
};

cogMenuRegistry.add("quotation-upload-menu", quotationUploaderMenuItem, {
    sequence: 30,
});
