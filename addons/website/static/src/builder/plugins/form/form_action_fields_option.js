import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { t, useProps } from "@odoo/owl";
import { useAsyncComputed } from "@web/core/utils/hooks";

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
        this.formInfo = useAsyncComputed(async () => {
            const { activeForm } = this.props;
            const el = this.env.getEditingElement();
            const formInfo = await this.prepareFormModel(el, activeForm);
            // A form saved before any record existed has no value yet. Fields
            // that the server fills by itself when empty are left as they are.
            const fields = formInfo.fields?.filter((field) => !field.serverDefault);
            this.dependencies.websiteFormOption.presetOldestRecords(el, { ...formInfo, fields });
            this.env.editor.shared.history.commit();
            this.props.onMissingRecord(
                formInfo.fields?.find((field) => this.isMissingRecord(field))
            );
            return {
                fields: [],
                formFields: [],
                successPage: undefined,
                ...formInfo,
            };
        });
    }
    /**
     * A required many2one field without any record to select cannot be
     * preset: the user has to create a record first.
     */
    isMissingRecord(field) {
        return field.type === "many2one" && field.required && !field.oldestRecordId;
    }
}
