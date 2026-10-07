import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { registry } from "@web/core/registry";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { uploadFiles } from "@web/views/view_button/upload_button";

export class AccountShareTargetItem extends ShareTargetItem {
    static template = "account.ShareTargetItem";
    static name = _t("Bill");
    static sequence = 2;

    setup() {
        super.setup();
        this.journals_domain = [["type", "=", "purchase"]];
        onWillStart(() => this.updateJournals());
    }

    async updateJournals() {
        this.state.journals = await this.orm
            .webSearchRead(this.modelName, this.journals_domain, {
                specification: { id: {}, display_name: {} },
                context: this.context
            })
            .then(({ records }) => records);
        this.state.selected_journal_id = this.state.journals.length
            ? this.state.journals[0]
            : false;
    }

    get modelName() {
        return "account.journal";
    }

    async process() {
        const journal = this.state.selected_journal_id;
        const action = await uploadFiles(this.env.services, {
            clickParams: { name: "create_document_from_attachment" },
            resModel: this.modelName,
            resIds: journal ? [journal.id] : [],
            context: { ...this.context, default_move_type: "in_invoice" },
            files: this.getFiles(),
        });
        if (action) {
            await this.action.doAction(action);
        }
    }

    onCompanyChange(companyId) {
        super.onCompanyChange(companyId);
        this.updateJournals();
    }

    get defaultState() {
        return { ...super.defaultState, journals: [], selected_journal_id: false };
    }

    get hasMultiJournals() {
        return this.state.journals.length > 1;
    }

    get journalRecordProps() {
        return {
            mode: "readonly",
            values: { journal: this.state.selected_journal_id },
            fieldNames: ["journal"],
            fields: {
                journal: {
                    name: "journal",
                    type: "many2one",
                    relation: this.modelName,
                    domain: this.journals_domain,
                },
            },
            hooks: {
                onRecordChanged: (record) => {
                    this.state.selected_journal_id = record.data.journal;
                },
            },
        };
    }
}

registry
    .category("share_target_items")
    .add(AccountShareTargetItem.template, AccountShareTargetItem);
