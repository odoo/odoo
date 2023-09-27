/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useCommand } from "@web/core/commands/command_hook";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { groupBy } from "@web/core/utils/arrays";
import { escape } from "@web/core/utils/strings";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";

export class StatusBarField extends Component {
    static template = "web.StatusBarField";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        ...standardFieldProps,
        canCreate: { type: Boolean, optional: true },
        canWrite: { type: Boolean, optional: true },
        displayName: { type: String, optional: true },
        isDisabled: { type: Boolean, optional: true },
        visibleSelection: { type: Array, optional: true },
        withCommand: { type: Boolean, optional: true },
        foldField: { type: String, optional: true },
        domain: { type: typeof Domain, optional: true },
    };
    static defaultProps = {
        visibleSelection: [],
    };

    setup() {
        if (this.props.withCommand) {
            const commandName = _t("Move to %s...", escape(this.displayName));
            useCommand(
                commandName,
                () => {
                    return {
                        placeholder: commandName,
                        providers: [
                            {
                                provide: () =>
                                    this.computeItems(false).map((value) => ({
                                        name: value.name,
                                        action: () => {
                                            this.selectItem(value);
                                        },
                                    })),
                            },
                        ],
                    };
                },
                {
                    category: "smart_action",
                    hotkey: "alt+shift+x",
                    isAvailable: () => !this.props.readonly && !this.props.isDisabled,
                }
            );
            useCommand(
                _t("Move to next %s", this.displayName),
                () => {
                    const options = this.computeItems(false);
                    const nextOption =
                        options[
                            options.findIndex(
                                (option) =>
                                    option.id ===
                                    (this.type === "many2one"
                                        ? this.props.record.data[this.props.name][0]
                                        : this.props.record.data[this.props.name])
                            ) + 1
                        ];
                    this.selectItem(nextOption);
                },
                {
                    category: "smart_action",
                    hotkey: "alt+x",
                    isAvailable: () => {
                        const options = this.computeItems(false);
                        return (
                            !this.props.readonly &&
                            !this.props.isDisabled &&
                            options[options.length - 1].id !==
                                (this.type === "many2one"
                                    ? this.props.record.data[this.props.name][0]
                                    : this.props.record.data[this.props.name])
                        );
                    },
                }
            );
        }

        if (this.type === "many2one") {
            this.specialData = useSpecialData((orm, props) => {
                const { foldField, name: fieldName, record } = props;
                const { relation } = record.fields[fieldName];
                const fieldNames = ["display_name"];
                if (foldField) {
                    fieldNames.push(foldField);
                }
                const value = props.record.data[fieldName];
                let domain = props.domain;
                if (domain.length && value) {
                    domain = Domain.or([[["id", "=", value[0]]], domain]).toList(
                        props.record.evalContext
                    );
                }
                return orm.searchRead(relation, domain, fieldNames);
            });
        }
    }

    get currentName() {
        switch (this.type) {
            case "many2one": {
                const item = this.options.find(
                    (item) =>
                        this.props.record.data[this.props.name] &&
                        item.id === this.props.record.data[this.props.name][0]
                );
                return item ? item.display_name : "";
            }
            case "selection": {
                const item = this.options.find(
                    (item) => item[0] === this.props.record.data[this.props.name]
                );
                return item ? item[1] : "";
            }
        }
        throw new Error("Unsupported field type for StatusBarField");
    }
    get options() {
        switch (this.type) {
            case "many2one":
                return this.specialData.data;
            case "selection":
                return this.props.record.fields[this.props.name].selection;
            default:
                return [];
        }
    }

    get displayName() {
        return this.props.record.fields[this.props.name].string;
    }
    get type() {
        return this.props.record.fields[this.props.name].type;
    }

    getDropdownItemClassNames(item) {
        const classNames = [];
        if (item.isSelected) {
            classNames.push("active");
        }
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
                isFolded: i[this.props.foldField],
            };
        });
        return items.map((item) => ({
            ...item,
            isSelected:
                this.props.record.data[this.props.name] &&
                item.id === this.props.record.data[this.props.name][0],
        }));
    }

    getVisibleSelection() {
        let selection = this.options;
        if (this.props.visibleSelection.length) {
            selection = selection.filter(
                (item) =>
                    this.props.visibleSelection.includes(item[0]) ||
                    item[0] === this.props.record.data[this.props.name]
            );
        }
        return selection.map((item) => ({
            id: item[0],
            name: item[1],
            isSelected: item[0] === this.props.record.data[this.props.name],
            isFolded: false,
        }));
    }

    computeItems(grouped = true) {
        let items = null;
        if (this.props.record.fields[this.props.name].type === "many2one") {
            items = this.getVisibleMany2Ones();
        } else {
            items = this.getVisibleSelection();
        }
        if (!grouped) {
            return items;
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

    async selectItem(item) {
        switch (this.props.record.fields[this.props.name].type) {
            case "many2one":
                await this.props.record.update({ [this.props.name]: [item.id, item.name] });
                break;
            case "selection":
                await this.props.record.update({ [this.props.name]: item.id });
                break;
        }
        return this.props.record.save();
    }

    onDropdownItemSelected(ev) {
        this.selectItem(ev.detail.payload);
    }
}

export const statusBarField = {
    component: StatusBarField,
    displayName: _t("Status"),
    supportedOptions: [
        {
            label: _t("Clickable"),
            name: "clickable",
            type: "boolean",
            default: true,
        },
        {
            label: _t("Fold field"),
            name: "fold_field",
            type: "field",
            availableTypes: ["boolean"],
        },
    ],
    supportedTypes: ["many2one", "selection"],
    isEmpty: (record, fieldName) => record.model.env.isSmall && !record.data[fieldName],
    extractProps: ({ attrs, options, viewType }, dynamicInfo) => ({
        canCreate: Boolean(attrs.can_create),
        canWrite: Boolean(attrs.can_write),
        isDisabled: !options.clickable,
        visibleSelection:
            attrs.statusbar_visible && attrs.statusbar_visible.trim().split(/\s*,\s*/g),
        withCommand: viewType === "form",
        foldField: options.fold_field,
        domain: dynamicInfo.domain(),
    }),
};

registry.category("fields").add("statusbar", statusBarField);
