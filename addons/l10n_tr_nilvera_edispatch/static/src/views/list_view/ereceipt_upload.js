/** @odoo-module */

import { Component, onWillStart } from "@odoo/owl";
import { FileUploader } from "@web/views/fields/file_handler";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class L10nTrEreceiptUploader extends Component {
    static template = "l10n_tr_nilvera_edispatch.L10nTrEreceiptUploader";
    static components = { FileUploader };

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
                `The file(s): ${this.invalidAttachments.join(", ")} must be of type XML.`,
                {
                    title: "Only XML files can be uploaded",
                    type: "danger",
                }
            );
        }
        if (this.attachmentIdsToProcess.length === 0) {
            return;
        }
        try {
            const action = await this.orm.call("stock.picking", "l10n_tr_import_ereceipts", [
                "",
                this.attachmentIdsToProcess,
            ]);

            if (action) {
                this.notification.add(action.msg, {
                    type: action.result ? "success" : "danger",
                    sticky: false,
                });
                if (action.result == true) {
                    this.action.doAction(action.action);
                }
            }
        } catch (e) {
            this.notification.add(e.data.message, {
                title: "Something went wrong. Please try again.",
                type: "danger",
            });
        } finally {
            this.attachmentIdsToProcess = [];
        }
    }
}

export class L10nTrNilveraEdispatchListController extends ListController {
    setup() {
        super.setup();
        onWillStart(async () => {
            const currentCompanyId = this.env.services.company.currentCompany.id;
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
    ...listView,
    Controller: L10nTrNilveraEdispatchListController,
    buttonTemplate: "l10n_tr_nilvera_edispatch.ListView.buttons",
};

registry.category("views").add("l10n_tr_edispatch_tree", L10nTrNilveraEdispatchListView);
