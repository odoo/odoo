import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class FormModelRequiredFieldAlert extends BaseOptionComponent {
    static template = "website.s_website_form_model_required_field_alert";
    static dependencies = ["websiteFormOption"];
    static props = {
        fieldName: String,
        modelName: String,
    };

    setup() {
        super.setup();
        this.state = useState({
            message: undefined,
        });
        this.fetchModels = this.dependencies.websiteFormOption.fetchModels;
        onWillStart(async () => this.handleProps(this.props));
        onWillUpdateProps(async (props) => this.handleProps(props));
    }
    async handleProps(props) {
        // Get list of website_form compatible models, needed for alert message.
        const el = this.env.getEditingElement();
        const models = await this.fetchModels(el);
        const model = models.find((model) => model.model === props.modelName);
        const actionName = model?.website_form_label || props.modelName;
        this.state.message = _t("The field “%(field)s” is mandatory for the action “%(action)s”.", {
            field: props.fieldName,
            action: actionName,
        });
    }
}
