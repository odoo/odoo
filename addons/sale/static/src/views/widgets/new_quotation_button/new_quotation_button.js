import { Component, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";

export class NewQuotationButton extends Component {
    static template = "sale.NewQuotationButton";

    props = useProps({
        ...standardWidgetProps,
        action: t.string(),
        string: t.string().optional(_t("New Quotation")),
        hotkey: t.string().optional("q"),
        title: t.string().optional(_t("Create new quotation")),
    });

    async onClick() {
        await this.env.services.action.doActionButton({
            resModel: this.props.record.resModel,
            resId: this.props.record.resId,
            name: this.props.action,
            type: "object",
        });
    }
}

export const newQuotationButton = {
    component: NewQuotationButton,

    extractProps: ({ attrs }) => ({
        action: attrs.action,
        string: attrs.string,
        hotkey: attrs.hotkey,
        title: attrs.title,
    }),
};

registry.category("view_widgets").add("new_quotation_button", newQuotationButton);
