import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FontAwesomeIconSelector } from "@web_studio/client_action/components/font_awesome_icon_selector/font_awesome_icon_selector";

export class NewButtonBoxDialog extends Component {
    static template = "web_studio.NewButtonBoxDialog";
    static components = {
        Dialog,
        FontAwesomeIconSelector,
        Many2XAutocomplete,
    };
    static props = {
        isAddingButtonBox: { type: Boolean },
        model: { type: Object },
        close: { type: Function },
    };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            icon: "fa fa-diamond",
            field: undefined,
        });
        this.text = undefined;
    }
    async update(selection) {
        if (!selection[0].display_name) {
            const resId = selection[0].id;
            const fields = ["display_name"];
            const record = await this.orm.read("ir.model.fields", [resId], fields);
            selection[0].display_name = record[0].display_name;
        }
        this.state.field = selection[0];
    }
    getDomain() {
        return [
            ["relation", "=", this.props.model.resModel],
            ["ttype", "in", ["many2one", "many2many"]],
            ["store", "=", true],
        ];
    }
    onConfirm() {
        if (!this.state.field?.id) {
            return this.notification.add(_t("Select a related field."));
        }
        if (this.props.isAddingButtonBox) {
            this.props.model.pushOperation({ type: "buttonbox" });
        }
        this.props.model.doOperation({
            type: "add",
            target: {
                tag: "div",
                attrs: {
                    class: "oe_button_box",
                },
            },
            position: "inside",
            node: {
                tag: "button",
                field: this.state.field.id,
                string: this.text || _t("New button"),
                attrs: {
                    class: "oe_stat_button",
                    // we don't need the 'fa' class here, but only the icon class
                    icon: this.state.icon.slice(3),
                },
            },
        });
        this.props.close();
    }
}
