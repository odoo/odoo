/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart } from "@odoo/owl";
import { FileUploader } from "@web/views/fields/file_handler";
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { StockListView } from "@stock/views/stock_empty_list_help";

export class L10nTrEreceiptUploader extends Component {
    static template = "l10n_tr_nilvera_edispatch.L10nTrEreceiptUploader";
    static components = { FileUploader };
    static props = {
        ...standardWidgetProps,
        slots: { type: Object, optional: true },
        record: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.attachmentIdsToProcess = [];
        this.invalidAttachments = [];
    }

    async onEreceiptFileUpload(file) {
        if (file.type != "text/xml") {
            this.invalidAttachments.push(file.name);
            return;
        }
        const file_data = {
            name: file.name,
            mimetype: file.type,
            datas: file.data,
        };
        const [attachmentId] = await this.orm.create("ir.attachment", [file_data]);
        this.attachmentIdsToProcess.push(attachmentId);
    }

    async onEreceiptUploadComplete() {
        if (this.invalidAttachments.length !== 0) {
            this.notification.add(
                _t("The file(s): %s must be of type XML.", this.invalidAttachments.join(", ")),
                {
                    title: _t("Only XML files can be uploaded"),
                    type: "danger",
                }
            );
            this.invalidAttachments = [];
        }
        if (this.attachmentIdsToProcess.length === 0) {
            return;
        }
        try {
            const result = await this.orm.call("stock.picking", "l10n_tr_import_ereceipts", [
                "",
                this.attachmentIdsToProcess,
            ]);

            if (result) {
                if (result.action) {
                    this.notification.add(_t("e-Receipt(s) Imported Successfully"), {
                        type: "success",
                    });
                    this.action.doAction(result.action);
                }
                if (result.skipped_xmls) {
                    this.notification.add(
                        _t(
                            "Error occured in reading following XML file(s): %s",
                            result.skipped_xmls.join(", ")
                        ),
                        { type: "danger", title: "e-Receipt(s) were not imported", sticky: true }
                    );
                }
            }
        } catch (e) {
            this.notification.add(e.data.message, {
                title: _t("Something went wrong. Please try again."),
                type: "danger",
            });
        } finally {
            this.attachmentIdsToProcess = [];
        }
    }
}

export class L10nTrNilveraEdispatchListController extends ListController {
    setup() {
        this.orm = useService("orm");
        super.setup();
        onWillStart(async () => {
            const currentCompanyId = user.activeCompany.id;
            this.data = await this.orm.searchRead(
                "res.company",
                [["id", "=", currentCompanyId]],
                ["country_code"]
            );
            this.countryCode = this.data[0].country_code;
        });
    }

    get isActionDisplayed() {
        return (
            this.countryCode === "TR" &&
            this.props.context.restricted_picking_type_code === "incoming"
        );
    }
}

L10nTrNilveraEdispatchListController.components = {
    ...L10nTrNilveraEdispatchListController.components,
    L10nTrEreceiptUploader,
};

export const L10nTrNilveraEdispatchListView = {
    ...StockListView,
    Controller: L10nTrNilveraEdispatchListController,
    buttonTemplate: "l10n_tr_nilvera_edispatch.ListView.buttons",
};

registry.category("views").add("l10n_tr_edispatch_tree", L10nTrNilveraEdispatchListView);
