/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { groupBy } from "@web/core/utils/arrays";
import { escape, sprintf } from "@web/core/utils/strings";
import { Domain } from "@web/core/domain";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class StatusBarField extends Component {
    setup() {
        if (this.props.addCommand) {
            this.initiateCommand();
        }
    }

    get dropdownClassNames() {
        const classNames = ["btn", "btn-secondary", "o_arrow_button"];
        if (this.props.isDisabled) {
            classNames.push("disabled");
        }
        return classNames.join(" ");
    }

    getVisibleMany2Ones() {
        let items = this.props.options;
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
        let selection = this.props.options;
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

        const groups = groupBy(items, (item) => item.isSelected || !item.isFolded);
        return {
            folded: groups.false || [],
            unfolded: groups.true || [],
        };
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
                return commandService.openPalette({
                    placeholder: name,
                    providers: [{ provide }],
                });
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
    addCommand: { type: Boolean, optional: true },
    canCreate: { type: Boolean, optional: true },
    canWrite: { type: Boolean, optional: true },
    displayName: { type: String, optional: true },
    isDisabled: { type: Boolean, optional: true },
    visibleSelection: { type: Array, optional: true },
    options: Array,
};
StatusBarField.components = {
    Dropdown,
    DropdownItem,
};

StatusBarField.displayName = _lt("Status");
StatusBarField.supportedTypes = ["many2one", "selection"];

StatusBarField.isEmpty = () => false;
StatusBarField.extractProps = (fieldName, record, attrs) => {
    const getOptions = () => {
        switch (record.fields[fieldName].type) {
            case "many2one":
                return record.preloadedData[fieldName];
            case "selection":
                return record.fields[fieldName].selection;
            default:
                return [];
        }
    };
    return {
        options: getOptions(),
        addCommand: record.activeFields[fieldName].viewType === "form",
        canCreate: Boolean(attrs.can_create),
        canWrite: Boolean(attrs.can_write),
        displayName: record.fields[fieldName].string,
        isDisabled: !attrs.options.clickable,
        visibleSelection:
            attrs.statusbar_visible && attrs.statusbar_visible.trim().split(/\s*,\s*/g),
    };
};

registry.category("fields").add("statusbar", StatusBarField);

export async function preloadStatusBar(orm, record, fieldName) {
    const fieldNames = ["id"];
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
    const records = await orm.searchRead(relation, domain, fieldNames);
    const foldMap = {};
    for (const rec of records) {
        foldMap[rec.id] = rec[foldField];
    }

    const nameGets = await orm.call(relation, "name_get", [records.map((rec) => rec.id)]);
    return nameGets.map((nameGet) => ({
        id: nameGet[0],
        name: nameGet[1],
        isFolded: foldField ? foldMap[nameGet[0]] : false,
    }));
}

registry.category("preloadedData").add("statusbar", {
    loadOnTypes: ["many2one"],
    extraMemoizationKey: (record, fieldName) => {
        return record.data[fieldName];
    },
    preload: preloadStatusBar,
});
