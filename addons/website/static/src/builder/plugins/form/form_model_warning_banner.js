import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

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
        onWillUpdateProps((props) => this.handleProps(props || this.props));
    }

    async handleProps(props) {
        const el = this.env.getEditingElement();
        const model = props.activeForm;

        if (!el || !model) {
            this.state.showWarning = false;
            return;
        }

        const formInfo = await this.prepareFormModel(el, model);
        const field = formInfo?.fields?.[0];

        if (!field) {
            return;
        }

        const hasNoRecords = !field.records?.length;
        if (hasNoRecords && field.noRecordMessage) {
            this.state.message = field.noRecordMessage;
            this.state.showWarning = true;
        }
    }
}
