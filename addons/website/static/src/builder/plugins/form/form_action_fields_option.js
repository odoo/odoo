import { onWillStart, onWillUpdateProps, proxy, useProps, t } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { _t } from "@web/core/l10n/translation";

export class FormActionFieldsOption extends BaseOptionComponent {
    static template = "website.s_website_form_form_action_fields_option";
    static dependencies = ["websiteFormOption"];
    props = useProps({
        activeForm: t.object().optional(),
        onMissingRecord: t.function(),
    });

    setup() {
        super.setup();
        this.prepareFormModel = this.dependencies.websiteFormOption.prepareFormModel;
        this.state = proxy({
            formInfo: {
                fields: [],
            },
        });
        onWillStart(() => this.getFormInfo(this.props));
        onWillUpdateProps((np) => this.getFormInfo(np));
    }
    async getFormInfo(props) {
        const el = this.env.getEditingElement();
        const formInfo = await this.prepareFormModel(el, props.activeForm);
        // A form saved before any record existed has no value yet.
        this.dependencies.websiteFormOption.presetOldestRecords(el, formInfo);
        Object.assign(
            this.state.formInfo,
            {
                fields: [],
                formFields: [],
                successPage: undefined,
            },
            formInfo
        );
        props.onMissingRecord(
            this.state.formInfo.fields.find((field) => this.isMissingRecord(field))
        );
    }
    /**
     * A required many2one field without any record to select cannot be
     * preset: the user has to create a record first.
     */
    isMissingRecord(field) {
        return field.type === "many2one" && field.required && !field.records.length;
    }
    /**
     * Generate the entries of the searchable select of a many2one field.
     */
    getRecordChoices(field) {
        const records = field.required
            ? field.records
            : [{ id: 0, display_name: _t("None") }, ...field.records];
        return records.map((record) => ({
            label: record.display_name,
            props: { actionValue: record.id.toString() },
            attrs: { "data-action-id": "addActionField", "data-action-value": record.id },
        }));
    }
}
