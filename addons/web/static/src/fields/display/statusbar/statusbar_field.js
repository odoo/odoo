// @ts-check
/** @odoo-module native */

import {
    onWillRender,
    onWillUnmount,
    useEffect,
    useExternalListener,
    useRef,
} from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/translation";
import { groupBy } from "@web/core/utils/collections/arrays";
import { measure, mutate } from "@web/core/utils/dom/layout_batch";
import { throttleForAnimation } from "@web/core/utils/timing";
import { registerField } from "@web/fields/_registry";
import { FieldComponent } from "@web/fields/field_component";
import { fieldHandleFor } from "@web/fields/field_handle";
import { archAttribute } from "@web/fields/field_options";
import { completeSelectedOptions } from "@web/fields/relational/selection_options";
import { useSpecialData } from "@web/fields/relational/special_data";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { getFieldDomain } from "@web/model/relational_model";
import { useCommand } from "@web/ui/commands";

/**
 * @typedef {import("@web/fields/standard_field_props").StandardFieldProps & {
 * domain?: [Array, Function];
 * foldField?: string;
 * isDisabled?: boolean;
 * visibleSelection?: string[];
 * withCommand?: boolean;
 * }} StatusBarFieldProps
 * @typedef StatusBarItem
 * @property {number} value
 * @property {string} label
 * @property {boolean} isFolded
 * @property {boolean} isSelected
 * @typedef StatusBarList
 * @property {string} label
 * @property {StatusBarItem[]} items
 */

/** @param {...HTMLElement} els */
const hide = (...els) => els.forEach((el) => el.classList.add("d-none"));

/** @param {...HTMLElement} els */
const show = (...els) => els.forEach((el) => el.classList.remove("d-none"));

/**
 * @param {StatusBarItem[] | null} a
 * @param {StatusBarItem[]} b
 * @returns {boolean}
 */
function sameStatusBarItems(a, b) {
    if (!a || a.length !== b.length) {
        return false;
    }
    return a.every(
        (item, i) =>
            item.value === b[i].value &&
            item.label === b[i].label &&
            item.isFolded === b[i].isFolded &&
            item.isSelected === b[i].isSelected,
    );
}

/** @param {any} component */
function useOverflowAdjust(component) {
    let status = "idle";
    /** @type {StatusBarItem[] | null} */
    let lastItems = null;
    /** @type {number | null} */
    let lastWidth = null;
    /** @type {StatusBarItem[] | null} */
    let sortedFrom = null;

    const adjust = () => {
        status = "adjusting";
        component.adjustVisibleItems();
        component.render();
    };

    useEffect(() => {
        if (status !== "shouldAdjust") {
            return;
        }
        measure(() => {
            if (status !== "shouldAdjust" || !component.rootRef.el?.isConnected) {
                return;
            }
            const width = component.rootRef.el.getBoundingClientRect().width;
            if (
                width === lastWidth &&
                sameStatusBarItems(lastItems, component.allItems)
            ) {
                status = "idle";
                return;
            }
            lastItems = component.allItems;
            lastWidth = width;
            mutate(() => {
                if (component.rootRef.el?.isConnected) {
                    adjust();
                }
            });
        });
    });

    onWillRender(() => {
        component.allItems = component.getAllItems();
        const itemsChanged = !sameStatusBarItems(sortedFrom, component.allItems);
        if (status !== "adjusting" || itemsChanged) {
            Object.assign(component.items, component.getSortedItems());
            sortedFrom = component.allItems;
            status = "shouldAdjust";
        } else {
            status = "idle";
        }
    });

    const throttledAdjust = throttleForAnimation(adjust);
    useExternalListener(window, "resize", throttledAdjust);
    onWillUnmount(() => throttledAdjust.cancel());
}

/** @extends {FieldComponent<StatusBarFieldProps>} */
export class StatusBarField extends FieldComponent {
    static template = "web.StatusBarField";
    static RELATION_LIMIT = 100;
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        ...standardFieldProps,
        domain: { type: [Array, Function], optional: true },
        foldField: { type: String, optional: true },
        isDisabled: { type: Boolean, optional: true },
        visibleSelection: { type: Array, element: String, optional: true },
        withCommand: { type: Boolean, optional: true },
        context: { type: Object, optional: true },
    };

    setup() {
        this.items = {};
        /** @type {StatusBarItem[]} */
        this.allItems = [];
        this.beforeRef = useRef("before");
        this.rootRef = useRef("root");
        this.afterRef = useRef("after");
        this.dropdownRef = useRef("dropdown");

        useOverflowAdjust(this);
        if (this.fieldDefinition.type === "many2one") {
            this.setupRelationData();
        }
        if (this.props.withCommand) {
            this.setupCommands();
        }
    }

    setupRelationData() {
        this.specialData = useSpecialData(async (orm, props) => {
            const { foldField, name: fieldName, record, context } = props;
            const field = fieldHandleFor(record, fieldName);
            const { relation } = field.definition;
            const fieldNames = this.getFieldNames(props);
            if (foldField) {
                fieldNames.push(foldField);
            }
            const value = field.value;
            let domain = getFieldDomain(record, fieldName, props.domain);
            domain = Domain.and([this.getDomain(props), domain]).toList();
            if (domain.length && value) {
                domain = Domain.or([[["id", "=", value.id]], domain]).toList(
                    record.evalContext,
                );
            }
            const options = await orm.searchRead(relation, domain, fieldNames, {
                context,
                limit: /** @type {any} */ (this.constructor).RELATION_LIMIT,
            });
            return completeSelectedOptions(
                options,
                value ? [value.id] : [],
                (option) => option.id,
                (ids) =>
                    orm.searchRead(relation, [["id", "in", ids]], fieldNames, {
                        context,
                        limit: ids.length,
                    }),
            );
        });
    }

    setupCommands() {
        const moveToCommandName = _t("Move to %s...", this.fieldDefinition.string);
        useCommand(
            moveToCommandName,
            () => ({
                placeholder: moveToCommandName,
                providers: [
                    {
                        provide: () =>
                            /** @type {any} */ (
                                this.getAllItems().map((item) => ({
                                    name: item.label,
                                    action: () => this.selectItem(item),
                                }))
                            ),
                    },
                ],
            }),
            {
                category: "smart_action",
                hotkey: "alt+shift+x",
                isAvailable: () => this.isReady && !this.props.isDisabled,
            },
        );
        useCommand(
            _t("Move to next %s", this.fieldDefinition.string),
            () => {
                const items = this.getAllItems();
                const nextIndex = items.findIndex((item) => item.isSelected) + 1;
                this.selectItem(items[nextIndex]);
            },
            {
                category: "smart_action",
                hotkey: "alt+x",
                isAvailable: () => {
                    if (!this.isReady || this.props.isDisabled) {
                        return false;
                    }
                    const items = this.getAllItems();
                    return Boolean(items.length) && !items.at(-1).isSelected;
                },
            },
        );
    }

    /** @returns {{ selection?: [string, string][], string: string, type: "many2one" | "selection" }} */
    get fieldDefinition() {
        return /** @type {any} */ (this.field.definition);
    }

    /**
     * @param {Record<string, any>} _props
     * @returns {import("@web/core/domain").DomainListRepr}
     */
    getDomain(_props) {
        return [];
    }

    /**
     * @param {Record<string, any>} _props
     * @returns {string[]}
     */
    getFieldNames(_props) {
        return ["display_name"];
    }

    adjustVisibleItems() {
        const itemEls = [
            ...this.rootRef.el.querySelectorAll(
                ".o_arrow_button:not(.dropdown-toggle)",
            ),
        ];
        const selectedIndex = itemEls.findIndex((el) =>
            el.classList.contains("o_arrow_button_current"),
        );
        const itemsBefore = itemEls.slice(selectedIndex + 2).reverse();
        const itemsAfter = itemEls.slice(0, Math.max(selectedIndex - 1, 0)).reverse();

        show(...itemEls);
        hide(this.dropdownRef.el, this.beforeRef.el);
        if (this.items.folded.length) {
            show(this.afterRef.el);
            itemEls.forEach((el) => el.classList.remove("o_first"));
        } else {
            hide(this.afterRef.el);
            itemEls[0]?.classList.add("o_first");
        }

        this.items.before = [];
        this.items.after = [...this.items.folded];
        const itemsToAssign = this.allItems.filter((item) => !item.isFolded);

        if (this.env.isSmall && this.items.inline.length) {
            show(this.dropdownRef.el);
            hide(this.beforeRef.el, this.afterRef.el, ...itemEls);
            return;
        }

        this._rowHeight = null;
        try {
            while (this.areItemsWrapping()) {
                if (itemsBefore.length) {
                    show(this.beforeRef.el);
                    hide(itemsBefore.shift());
                    this.items.before.push(itemsToAssign.shift());
                } else if (itemsAfter.length) {
                    show(this.afterRef.el);
                    hide(itemsAfter.pop());
                    this.items.after.unshift(itemsToAssign.pop());
                } else {
                    show(this.dropdownRef.el);
                    hide(this.beforeRef.el, this.afterRef.el, ...itemEls);
                    break;
                }
            }
        } finally {
            this._rowHeight = null;
        }
    }

    areItemsWrapping() {
        const root = this.rootRef.el;
        if (this._rowHeight === null) {
            const firstItem = root.querySelector(":scope > :not(.d-none)");
            if (!firstItem) {
                return false;
            }
            this._rowHeight = firstItem.getBoundingClientRect().height;
        }
        return root.getBoundingClientRect().height > this._rowHeight;
    }

    /** @returns {StatusBarItem[]} */
    getAllItems() {
        const { foldField } = this.props;
        const currentValue = this.field.value;
        if (this.fieldDefinition.type === "many2one") {
            return this.specialData.data.map((option) => ({
                value: option.id,
                label: option.display_name,
                isFolded: option[foldField],
                isSelected: Boolean(currentValue && option.id === currentValue.id),
            }));
        } else {
            let { selection } = this.fieldDefinition;
            const { visibleSelection } = this.props;
            if (visibleSelection?.length) {
                selection = selection.filter(
                    ([value]) =>
                        value === currentValue || visibleSelection.includes(value),
                );
            }
            return /** @type {any} */ (
                selection.map(([value, label]) => ({
                    value,
                    label,
                    isFolded: false,
                    isSelected: value === currentValue,
                }))
            );
        }
    }

    getCurrentLabel() {
        return this.allItems.find((item) => item.isSelected)?.label || _t("More");
    }

    /** @param {StatusBarItem} item */
    getDropdownItemClassNames(item) {
        const classNames = [];
        if (item.isSelected) {
            classNames.push("active");
        }
        if (item.isSelected || !this.isReady || this.props.isDisabled) {
            classNames.push("disabled");
        }
        return classNames.join(" ");
    }

    getSortedItems() {
        const before = [];
        const after = [];
        const { true: inline = [], false: folded = [] } = groupBy(
            this.allItems,
            (item) => item.isSelected || !item.isFolded,
        );
        inline.reverse();
        after.push(...folded);
        return { inline, before, after, folded };
    }

    get isReady() {
        return !this.specialData || this.specialData.isReady;
    }

    /** @param {StatusBarItem} item */
    async selectItem(item) {
        if (!this.isReady || this.props.isDisabled) {
            return;
        }
        const value =
            this.fieldDefinition.type === "many2one"
                ? { id: item.value, display_name: item.label }
                : item.value;
        await this.field.update(value);
        await this.props.record.save();
    }

    /** @param {CustomEvent<{ payload: StatusBarItem }>} ev */
    onDropdownItemSelected(ev) {
        this.selectItem(ev.detail.payload);
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
export const statusBarField = {
    component: StatusBarField,
    displayName: _t("Status"),
    supportedOptions: [
        {
            label: _t("Clickable"),
            name: "clickable",
            type: "boolean",
            default: false,
        },
        {
            label: _t("Fold field"),
            name: "fold_field",
            type: "field",
            isRelationalField: true,
            availableTypes: ["boolean"],
            help: _t(
                "Boolean field from the model used in the relation, which indicates whether the state is folded or not.",
            ),
        },
    ],
    supportedAttributes: [
        archAttribute("statusbar_visible", _t("Always-visible steps"), {
            help: _t(
                "Comma-separated selection values that stay inline even when folded.",
            ),
        }),
    ],
    supportedTypes: ["many2one", "selection"],
    extractProps: ({ attrs, options, viewType }, dynamicInfo) => ({
        isDisabled: !options.clickable || dynamicInfo.readonly,
        visibleSelection: attrs.statusbar_visible?.trim()
            ? attrs.statusbar_visible.trim().split(/\s*,\s*/g)
            : undefined,
        withCommand: viewType === "form",
        foldField: options.fold_field,
        domain: dynamicInfo.domain,
        context: dynamicInfo.context,
    }),
};

registerField("statusbar", statusBarField);
