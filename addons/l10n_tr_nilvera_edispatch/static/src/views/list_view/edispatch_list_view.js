/** @odoo-module */

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { onWillStart } from "@odoo/owl";
import { MailAttachments } from "@account/components/mail_attachments/mail_attachments";

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
        return this.countryCode === "TR";
    }
}

export const L10nTrNilveraEdispatchListView = {
    ...listView,
    Controller: L10nTrNilveraEdispatchListController,
    buttonTemplate: "l10n_tr_nilvera_edispatch.ListView.buttons",
};

export class L10nTrNilveraEreceiptUploader extends MailAttachments {
    static template = "l10n_tr_nilvera_edispatch.EreceiptUploader";

    onFileUploaded(files) {
        const extraFiles = [];
        for (const file of files) {
            if (file.mimetype !== "application/xml") {
                const error_msg = `${file.filename} must be an XML file.`;
                return this.notification.add(error_msg, {
                    title: "Invalid File type",
                    type: "danger",
                });
            }

            extraFiles.push({
                id: file.id,
                name: file.filename,
                mimetype: file.mimetype,
                placeholder: false,
                manual: true,
            });
        }
        this.props.record.update({ [this.props.name]: this.getValue().concat(extraFiles) });
    }

    async onWillUnmount() {
        // Unlink attachments.
        this.getValue().forEach((item) => {
            if (item.manual) {
                this.attachmentIdsToUnlink.add(item.id);
            }
        });
        if (this.attachmentIdsToUnlink.size > 0) {
            await this.orm.unlink("ir.attachment", Array.from(this.attachmentIdsToUnlink));
        }
    }
}

registry.category("views").add("edespatch_tree", L10nTrNilveraEdispatchListView);
registry.category("fields").add("ereceipt_upload", {
    component: L10nTrNilveraEreceiptUploader,
});
