import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useState } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";

export class FormModelWarningBanner extends BaseOptionComponent {
    static template = "website.FormModelWarningBanner";
    static dependencies = ["websiteFormOption"];
    static props = {
        models: Array,
        activeForm: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.state = useState({
            showWarning: false,
            message: "",
        });
        this.prepareFormModel = this.dependencies.websiteFormOption.prepareFormModel;
        onWillStart(() => this.handleProps(this.props));
        onWillUpdateProps((nextProps) => this.handleProps(nextProps));
    }

    async handleProps(props = this.props) {
        Object.assign(this.state, {
            showWarning: false,
            message: "",
        });

        const el = this.env.getEditingElement();
        const model = props.activeForm;

        if (!el || !model) {
            return;
        }

        const formInfo = await this.prepareFormModel(el, model);
        const field = formInfo?.fields?.[0];
        const shouldWarn =
            !!field &&
            field.name !== "email_to" &&
            field.required &&
            (field.records?.length || 0) === 0;

        if (shouldWarn) {
            this.state.message =
                field.noRecordMessage ||
                _t(
                    "To be able to use this model in a form, you must first create a record for it."
                );
            this.state.showWarning = true;
        }
    }
}
