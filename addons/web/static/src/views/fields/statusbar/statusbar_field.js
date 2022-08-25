/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { groupBy } from "@web/core/utils/arrays";
import { escape, sprintf } from "@web/core/utils/strings";
import { Domain } from "@web/core/domain";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class StatusBarField extends Component {
    setup() {
        if (this.props.record.activeFields[this.props.name].viewType === "form") {
            this.initiateCommand();
        }
    }

    get currentName() {
        switch (this.props.record.fields[this.props.name].type) {
            case "many2one": {
                const item = this.options.find((item) => item.isSelected);
                return item ? item.name : "";
            }
            case "selection": {
                const item = this.options.find((item) => item[0] === this.props.value);
                return item ? item[1] : "";
            }
        }
        throw new Error("Unsupported field type for StatusBarField");
    }
    get options() {
        switch (this.props.record.fields[this.props.name].type) {
            case "many2one":
                return this.props.record.preloadedData[this.props.name];
            case "selection":
                return this.props.record.fields[this.props.name].selection;
            default:
                return [];
        }
    }

    getDropdownItemClassNames(item) {
        const classNames = [
            "btn",
            item.isSelected ? "btn-primary" : "btn-secondary",
            "o_arrow_button",
        ];
        if (item.isSelected || this.props.isDisabled) {
            classNames.push("disabled");
        }
        return classNames.join(" ");
    }

    getVisibleMany2Ones() {
        let items = this.options;
        // FIXME: do this somewhere else
        items = items.map((i) => {
            return {
                id: i.id,
                name: i.display_name,
                isFolded: i.fold,
            };
        });
        return items.map((item) => ({
            ...item,
            isSelected: this.props.value && item.id === this.props.value[0],
        }));
    }

    getVisibleSelection() {
        let selection = this.options;
        if (this.props.visibleSelection.length) {
            selection = selection.filter(
                (item) =>
                    this.props.visibleSelection.includes(item[0]) || item[0] === this.props.value
            );
        }
        return selection.map((item) => ({
            id: item[0],
            name: item[1],
            isSelected: item[0] === this.props.value,
            isFolded: false,
        }));
    }

    computeItems() {
        let items = null;
        if (this.props.type === "many2one") {
            items = this.getVisibleMany2Ones();
        } else {
            items = this.getVisibleSelection();
        }

        if (this.env.isSmall) {
            return {
                folded: items,
                unfolded: [],
            };
        } else {
            const groups = groupBy(items, (item) => item.isSelected || !item.isFolded);
            return {
                folded: groups.false || [],
                unfolded: groups.true || [],
            };
        }
    }

    selectItem(item) {
        switch (this.props.type) {
            case "many2one":
                this.props.update([item.id, item.name]);
                break;
            case "selection":
                this.props.update(item.id);
                break;
        }
    }

    onDropdownItemSelected(ev) {
        this.selectItem(ev.detail.payload);
    }

    initiateCommand() {
        try {
            const commandService = useService("command");
            const provide = () => {
                return this.computeItems().unfolded.map((value) => ({
                    name: value.name,
                    action: () => {
                        this.selectItem(value);
                    },
                }));
            };
            const name = sprintf(this.env._t(`Move to %s...`), escape(this.props.displayName));
            const action = () => {
                return {
                    placeholder: name,
                    providers: [{ provide }],
                };
            };
            const options = {
                category: "smart_action",
                hotkey: "alt+shift+x",
            };
            commandService.add(name, action, options);
        } catch {
            console.log("Could not add command to service");
        }
    }
}

StatusBarField.template = "web.StatusBarField";
StatusBarField.defaultProps = {
    visibleSelection: [],
};
StatusBarField.props = {
    ...standardFieldProps,
    canCreate: { type: Boolean, optional: true },
    canWrite: { type: Boolean, optional: true },
    displayName: { type: String, optional: true },
    isDisabled: { type: Boolean, optional: true },
    visibleSelection: { type: Array, optional: true },
};
StatusBarField.components = {
    Dropdown,
    DropdownItem,
};

StatusBarField.displayName = _lt("Status");
StatusBarField.supportedTypes = ["many2one", "selection"];

StatusBarField.isEmpty = (record, fieldName) => {
    return record.model.env.isSmall ? !record.data[fieldName] : false;
};
StatusBarField.extractProps = ({ attrs, field }) => {
    return {
        canCreate: Boolean(attrs.can_create),
        canWrite: Boolean(attrs.can_write),
        displayName: field.string,
        isDisabled: !attrs.options.clickable,
        visibleSelection:
            attrs.statusbar_visible && attrs.statusbar_visible.trim().split(/\s*,\s*/g),
    };
};

registry.category("fields").add("statusbar", StatusBarField);

export async function preloadStatusBar(orm, record, fieldName) {
    const fieldNames = ["id", "display_name"];
    const foldField = record.activeFields[fieldName].options.fold_field;
    if (foldField) {
        fieldNames.push(foldField);
    }

    const context = record.evalContext;
    let domain = record.getFieldDomain(fieldName).toList(context);
    if (domain.length && record.data[fieldName]) {
        domain = Domain.or([[["id", "=", record.data[fieldName][0]]], domain]).toList(context);
    }

    const relation = record.fields[fieldName].relation;
    return await orm.searchRead(relation, domain, fieldNames);
}

registry.category("preloadedData").add("statusbar", {
    loadOnTypes: ["many2one"],
    extraMemoizationKey: (record, fieldName) => {
        return record.data[fieldName];
    },
    preload: preloadStatusBar,
});
