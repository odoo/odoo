import { Component, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class NewQuotationButton extends Component {
    static template = "sale.NewQuotationButton";

    props = useProps({
        ...standardWidgetProps,
        action: t.string(),
        type: t.string().optional("object"),
        string: t.string().optional("New Quotation"),
        hotkey: t.string().optional("q"),
        title: t.string().optional("Create new quotation"),
    });

    async onClick() {
        await this.env.services.action.doActionButton({
            resModel: this.props.record.resModel,
            resId: this.props.record.resId,
            name: this.props.action,
            type: this.props.type,
        });
    }
}

export const newQuotationButton = {
    component: NewQuotationButton,

    extractProps: ({ attrs }) => ({
        action: attrs.action,
        type: attrs.type,
        string: attrs.string,
        hotkey: attrs.hotkey,
        title: attrs.title,
    }),
};

registry.category("view_widgets").add("new_quotation_button", newQuotationButton);
