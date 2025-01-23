import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { DocumentFileUploader } from "@account/components/document_file_uploader/document_file_uploader";

export class PurchaseFileUploader extends DocumentFileUploader {
    static template = "purchase.PurchaseFileUploader";
    static props = {
        ...DocumentFileUploader.props,
        btnClass: { type: String, optional: true },
        linkText: { type: String, optional: true },
        togglerTemplate: { type: String, optional: true },
    };

    getResModel() {
        return "account.journal";
    }

    getExtraContext() {
        const extraContext = super.getExtraContext();
        const record_data = this.props.record ? this.props.record.data : false;
        return {
            ...extraContext,
            default_purchase_id: record_data ? record_data.id : false,
            default_move_type: 'in_invoice',
        };
    }

}

export const purchaseFileUploader = {
    component: PurchaseFileUploader,
    extractProps: ({ attrs }) => ({
        togglerTemplate: attrs.template || "purchase.PurchaseUploadLink",
        btnClass: attrs.btnClass || "",
        linkText: attrs.title || _t("Upload Bill"),
    }),
};

registry.category("view_widgets").add("purchase_file_uploader", purchaseFileUploader);
