import { domainField, DomainField, domainFieldProps } from "@web/views/fields/domain/domain_field";
import { props, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { registry } from "@web/core/registry";
import { MailingFilterFormViewDialog } from "../../components/mailing_filter_form_view_dialog/mailing_filter_form_view_dialog";

/**
 * Domain field that provides a save button which allows
 * to save a crafted domain by the user as a dynamic list
 * (mailing.filter).
 *
 * The model_id field name must be passed in the options.
 * That field defines how the model_id is stored in
 * the record.
 *
 * NOTE: the used record must have a field `mailing_filter_ids`
 * (e.g. `mailing.mailing` or `marketing.campaign`),
 * as the newly created domain will be set to that field.
 */
export class DomainSavableField extends DomainField {
    static template = "mass_mailing.DomainSavableField";
    props = props({
        ...domainFieldProps,
        modelIdField: t.string(),
    });

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        useRecordObserver(async () => {
            this.state.showSaveButton = this.getDomain() !== "[]";
        });
        this.saveBtnLabel = _t("Save as a Dynamic List");
    }

    /**
     * Open a simplified form view to save the crafted domain
     * as a new mailing.filter (dynamic list).
     * If `record._saveForLater` is true, the list is only saved
     * and a notification is displayed, otherwise, the list is
     * saved and applied to the parent record as its recipients.
     */
    async openSaveMailingFilterDialog() {
        const record = this.props.record;
        if (!record.resId || record.isDirty) {
            await record.save();
        }
        this.dialogService.add(MailingFilterFormViewDialog, {
            title: _t("Save As a Dynamic List"),
            resModel: "mailing.filter",
            context: {
                ...this.props.context,
                form_view_ref: "mass_mailing.mailing_filter_view_form_simplified",
                default_mailing_model_id: this.props.record.data[this.props.modelIdField]?.id,
                default_mailing_domain: this.getDomain(),
            },
            onRecordSavedForLater: async () => {
                this.notification.add(_t("Dynamic List saved!"), { type: "success" });
                await this.props.record.load();
                return;
            },
            onRecordSaved: async (record) => {
                this.props.record.update({ mailing_filter_ids: [[4, record.resId]] });
            },
        });
    }
}

export const domainSavableField = {
    ...domainField,
    component: DomainSavableField,
    supportedOptions: [
        ...domainField.supportedOptions,
        {
            label: _t("Model id"),
            name: "model_id",
            type: "field",
            availableTypes: ["many2one"],
        },
    ],
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...domainField.extractProps(fieldInfo, dynamicInfo),
        modelIdField: fieldInfo.options.model_id,
    }),
};

registry.category("fields").add("domain_savable", domainSavableField);
