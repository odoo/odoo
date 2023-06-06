/** @odoo-module **/

import { Component, onWillRender, useEffect, useExternalListener, useRef } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useCommand } from "@web/core/commands/command_hook";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { groupBy } from "@web/core/utils/arrays";
import { escape } from "@web/core/utils/strings";
import { throttleForAnimation } from "@web/core/utils/timing";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";

/**
 * @typedef {import("../standard_field_props").StandardFieldProps & {
 *  domain?: typeof Domain;
 *  foldField?: string;
 *  isDisabled?: boolean;
 *  visibleSelection?: string[];
 *  withCommand?: boolean;
 * }} StatusBarFieldProps
 *
 * @typedef StatusBarItem
 * @property {number} value
 * @property {string} label
 * @property {boolean} isFolded
 * @property {boolean} isSelected
 *
 * @typedef StatusBarList
 * @property {string} label
 * @property {StatusBarItem[]} items
 */

/**
 * @param {...HTMLElement} els
 */
const hide = (...els) => els.forEach((el) => el.classList.add("d-none"));

/**
 * @param {...HTMLElement} els
 */
const show = (...els) => els.forEach((el) => el.classList.remove("d-none"));

/** @extends {Component<StatusBarFieldProps>} */
export class StatusBarField extends Component {
    static template = "web.StatusBarField";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        ...standardFieldProps,
        domain: { type: typeof Domain, optional: true },
        foldField: { type: String, optional: true },
        isDisabled: { type: Boolean, optional: true },
        visibleSelection: { type: Array, element: String, optional: true },
        withCommand: { type: Boolean, optional: true },
    };

    setup() {
        // Properties
        this.items = {};
        this.beforeRef = useRef("before");
        this.rootRef = useRef("root");
        this.afterRef = useRef("after");
        this.dropdownRef = useRef("dropdown");

        // Resize listeners
        let status = "idle";
        const adjust = () => {
            status = "adjusting";
            this.adjustVisibleItems();
            this.render();
            browser.requestAnimationFrame(() => (status = "idle"));
        };

        useEffect(
            () => status === "shouldAdjust" && adjust(),
            () => [status]
        );

        onWillRender(() => {
            if (status !== "adjusting") {
                Object.assign(this.items, this.getSortedItems());
                status = "shouldAdjust";
            }
        });

        useExternalListener(window, "resize", throttleForAnimation(adjust));

        // Special data
        if (this.field.type === "many2one") {
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

        // Command palette
        if (this.props.withCommand) {
            const moveToCommandName = _t("Move to %s...", escape(this.field.string));
            useCommand(
                moveToCommandName,
                () => ({
                    placeholder: moveToCommandName,
                    providers: [
                        {
                            provide: () =>
                                this.getAllItems().map((item) => ({
                                    name: item.label,
                                    action: () => this.selectItem(item),
                                })),
                        },
                    ],
                }),
                {
                    category: "smart_action",
                    hotkey: "alt+shift+x",
                    isAvailable: () => !this.props.isDisabled,
                }
            );
            useCommand(
                _t("Move to next %s", this.field.string),
                () => {
                    const items = this.getAllItems();
                    const nextIndex = items.findIndex((item) => item.isSelected) + 1;
                    this.selectItem(items[nextIndex]);
                },
                {
                    category: "smart_action",
                    hotkey: "alt+x",
                    isAvailable: () =>
                        !this.props.isDisabled && !this.getAllItems().at(-1).isSelected,
                }
            );
        }
    }

    /**
     * @returns {{ selection?: [string, string][], string: string, type: "many2one" | "selection" }}
     */
    get field() {
        return this.props.record.fields[this.props.name];
    }

    /**
     * Determines what items must be visible and how they must be displayed.
     * There are 4 main scenarios:
     *
     * 1. All items can be displayed inline, no modification in the UI;
     *
     * The following scenarios imply that the viewport is too small to display
     * all items in one line. Adjustments are made incrementally:
     *
     * 2. Items up to 1 before the currently selected item are combined in a dropdown;
     *
     * 3. Items up to 1 after the currently selected item are combined in a dropdown,
     * along with the initially folded items;
     *
     * 4. If that still doesn't suffice: all items are combined in a single dropdown.
     */
    adjustVisibleItems() {
        // Get all visible buttons
        const itemEls = [
            ...this.rootRef.el.querySelectorAll(".o_arrow_button:not(.dropdown-toggle)"),
        ];
        const selectedIndex = itemEls.findIndex((el) =>
            el.classList.contains("o_arrow_button_current")
        );
        const itemsBefore = itemEls.slice(selectedIndex + 2).reverse();
        const itemsAfter = itemEls.slice(0, Math.max(selectedIndex - 1, 0)).reverse();

        // Reset hidden elements
        show(...itemEls);
        hide(this.dropdownRef.el, this.beforeRef.el);
        if (this.items.folded.length) {
            show(this.afterRef.el);
            itemEls.forEach((el) => el.classList.remove("o_first"));
        } else {
            hide(this.afterRef.el);
        }

        // Reset items variables
        this.items.before = [];
        this.items.after = [...this.items.folded];
        const itemsToAssign = this.getAllItems().filter((item) => !item.isFolded);

        while (this.areItemsWrapping()) {
            if (itemsBefore.length) {
                // Case 1: elements before can be hidden
                show(this.beforeRef.el);
                hide(itemsBefore.shift());
                this.items.before.push(itemsToAssign.shift());
            } else if (itemsAfter.length) {
                // Case 2: elements before are hidden, elements after can be hidden
                show(this.afterRef.el);
                hide(itemsAfter.pop());
                this.items.after.unshift(itemsToAssign.pop());
            } else {
                // Last resort: no elements can be hidden => fallback to single dropdown
                show(this.dropdownRef.el);
                hide(this.beforeRef.el, this.afterRef.el, ...itemEls);
                break;
            }
        }
    }

    areItemsWrapping() {
        const root = this.rootRef.el;
        const firstItem = root.querySelector(":scope > :not(.d-none)");
        if (!firstItem) {
            return false;
        }
        const { height: currentHeight } = root.getBoundingClientRect();
        const { height: targetHeight } = firstItem.getBoundingClientRect();
        return currentHeight > targetHeight;
    }

    /**
     * @returns {StatusBarItem[]}
     */
    getAllItems() {
        const { foldField, name, record } = this.props;
        const currentValue = record.data[name];
        if (this.field.type === "many2one") {
            // Many2one
            return this.specialData.data.map((option) => ({
                value: option.id,
                label: option.display_name,
                isFolded: option[foldField],
                isSelected: Boolean(currentValue && option.id === currentValue[0]),
            }));
        } else {
            // Selection
            let { selection } = this.field;
            const { visibleSelection } = this.props;
            if (visibleSelection?.length) {
                selection = selection.filter(
                    ([value]) => value === currentValue || visibleSelection.includes(value)
                );
            }
            return selection.map(([value, label]) => ({
                value,
                label,
                isFolded: false,
                isSelected: value === currentValue,
            }));
        }
    }

    getCurrentLabel() {
        return this.getAllItems().find((item) => item.isSelected)?.label || _t("More");
    }

    /**
     * @param {StatusBarItem} item
     */
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

    /**
     * @param {StatusBarItem} item
     */
    getItemTooltip(item) {
        if (item.isSelected) {
            return _t("Current state");
        }
        if (this.props.isDisabled) {
            return _t("Not active state");
        }
        return _t("Not active state, click to change it");
    }

    getSortedItems() {
        const before = [];
        const after = [];
        const { true: inline = [], false: folded = [] } = groupBy(
            this.getAllItems(),
            (item) => item.isSelected || !item.isFolded
        );
        inline.reverse(); // CSS rules account for this list to be reversed
        after.push(...folded);
        return { inline, before, after, folded };
    }

    /**
     * @param {StatusBarItem} item
     */
    async selectItem(item) {
        const { name, record } = this.props;
        const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
        await record.update({ [name]: value });
        await record.save();
    }

    /**
     * @param {CustomEvent<{ payload: StatusBarItem }>} ev
     */
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
    isEmpty: (record, fieldName) => !record.data[fieldName],
    extractProps: ({ attrs, options, viewType }, dynamicInfo) => ({
        isDisabled: !options.clickable || dynamicInfo.readonly,
        visibleSelection: attrs.statusbar_visible?.trim().split(/\s*,\s*/g),
        withCommand: viewType === "form",
        foldField: options.fold_field,
        domain: dynamicInfo.domain(),
    }),
};

registry.category("fields").add("statusbar", statusBarField);
