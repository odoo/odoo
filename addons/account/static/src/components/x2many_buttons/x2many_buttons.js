/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

class X2ManyButtons extends Component {
    static template = "account.X2ManyButtons";
    static props = {
        ...standardFieldProps,
        treeLabel: { type: String },
    };

    setup() {
        this.action = useService("action");
    }

    async openTreeAndDiscard() {
        const ids = this.currentField.currentIds;
        await this.props.record.discard();
        this.action.doAction({
            name: this.props.treeLabel,
            type: "ir.actions.act_window",
            res_model: this.currentField.resModel,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [["id", "in", ids]],
        });
    }

    async openFormAndDiscard(id) {
        await this.props.record.discard();
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: this.currentField.resModel,
            res_id: id,
            views: [[false, "form"]],
        });
    }

    get currentField() {
        return this.props.record.data[this.props.name];
    }
}

X2ManyButtons.template = "account.X2ManyButtons";
registry.category("fields").add("x2many_buttons", {
    component: X2ManyButtons,
    relatedFields: [{ name: "display_name", type: "char" }],
    extractProps: ({ string }) => ({ treeLabel: string || _t("Records") }),
});
