/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { many2OneField, Many2OneField } from "../many2one/many2one_field";

import { Component } from "@odoo/owl";
import { AvatarMany2XAutocomplete } from "@web/views/fields/relational_utils";

export class Many2OneAvatarField extends Component {
    static template = "web.Many2OneAvatarField";
    static components = {
        Many2OneField,
    };
    static props = {
        ...Many2OneField.props,
    };

    get relation() {
        return this.props.relation || this.props.record.fields[this.props.name].relation;
    }
    get many2OneProps() {
        return Object.fromEntries(
            Object.entries(this.props).filter(
                ([key, _val]) => key in this.constructor.components.Many2OneField.props
            )
        );
    }
}

export const many2OneAvatarField = {
    ...many2OneField,
    component: Many2OneAvatarField,
    extractProps(fieldInfo) {
        const props = many2OneField.extractProps(...arguments);
        props.canOpen = fieldInfo.viewType === "form";
        return props;
    },
};

export class Many2OneFieldPopover extends Many2OneField {
    static props = {
        ...Many2OneField.props,
        close: { type: Function },
    };
    static components = {
        Many2XAutocomplete: AvatarMany2XAutocomplete,
    };
    get Many2XAutocompleteProps() {
        return {
            ...super.Many2XAutocompleteProps,
            dropdown: false,
            autofocus: true,
        };
    }

    async updateRecord(value) {
        const updatedValue = await super.updateRecord(...arguments);
        await this.props.record.save();
        return updatedValue;
    }
}

export class KanbanMany2OneAvatarField extends Many2OneAvatarField {
    static template = "web.KanbanMany2OneAvatarField";
    static props = {
        ...Many2OneAvatarField.props,
        isEditable: { type: Boolean, optional: true },
    };
    setup() {
        super.setup();
        this.popover = usePopover(Many2OneFieldPopover, {
            popoverClass: "o_m2o_tags_avatar_field_popover",
            closeOnClickAway: (target) => !target.closest(".modal"),
        });
    }
    get popoverProps() {
        const props = {
            ...this.props,
            readonly: false,
        };
        delete props.isEditable;
        return props;
    }
    openPopover(ev) {
        if (!this.props.isEditable) {
            return;
        }
        this.popover.open(ev.currentTarget, {
            ...this.popoverProps,
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            placeholder: _t("Search user..."),
        });
    }
}

export const kanbanMany2OneAvatarField = {
    ...many2OneField,
    component: KanbanMany2OneAvatarField,
    additionalClasses: ["o_field_many2one_avatar_kanban"],
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneAvatarField.extractProps(...arguments);
        props.isEditable = !dynamicInfo.readonly;
        return props;
    },
};
registry.category("fields").add("many2one_avatar", many2OneAvatarField);
registry.category("fields").add("kanban.many2one_avatar", kanbanMany2OneAvatarField);
