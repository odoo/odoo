import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One } from "../many2one/many2one";
import { usePopover } from "@web/core/popover/popover_hook";

class KanbanMany2OneAvatarFieldAssignPopover extends Component {
    static template = `web.${this.name}`;
    static components = { Many2One };
    static props = ["*"];
    static defaultProps = {};

    get many2oneProps() {
        return {
            ...this.props,
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            dropdown: false,
            placeholder: this.placeholder,
            readonly: false,
        };
    }

    get placeholder() {
        return _t("Search user...");
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }
}

export class KanbanMany2OneAvatarField extends Component {
    static template = `web.${this.name}`;
    static components = { Many2One };
    static props = ["*"];
    static defaultProps = {};

    setup() {
        this.assignPopover = usePopover(KanbanMany2OneAvatarFieldAssignPopover, {
            popoverClass: "o_m2o_tags_avatar_field_popover",
        });
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }

    openAssignPopover(target) {
        this.assignPopover.open(target, this.props);
    }
}

registry.category("fields").add("kanban.many2one_avatar", {
    component: KanbanMany2OneAvatarField,
    displayName: _t("Many2One Avatar"),
    extractProps(_, { readonly }) {
        return {
            isEditable: !readonly,
        };
    },
    supportedTypes: ["many2one"],
});
