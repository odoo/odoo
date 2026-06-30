import { useRef } from "@web/owl2/utils";
import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import { BuilderListDialog } from "@html_builder/core/building_blocks/builder_list_dialog";
import { useBuilderComponent, useInputBuilderComponent } from "@html_builder/core/utils";
import { isSmallInteger } from "@html_builder/utils/utils";
import { Component, onPatched, props, t, xml, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useSortable } from "@web/core/utils/sortable_owl";
import { useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { localeCompare } from "@web/core/l10n/utils";

/**
 * Focus the last added input item to a list container.
 *
 * @param {string} refName The list container's ref.
 */
export function useAutoFocusNewItem(refName) {
    const ref = useRef(refName);
    let nbRow = 0;
    function autofocus() {
        const prevSize = nbRow;
        const rowEls = ref.el?.querySelectorAll(".o_row_draggable") || [];
        nbRow = rowEls.length;
        if (nbRow <= prevSize) {
            return;
        }
        const newRowEl = rowEls[nbRow - 1];
        const newInputEl = newRowEl.querySelector("input, textarea");
        if (newInputEl) {
            newInputEl.focus();
            if (!["checkbox", "number"].includes(newInputEl.type)) {
                newInputEl.selectionStart = newInputEl.selectionEnd = newInputEl.value.length;
            }
        }
    }
    onPatched(autofocus);
}

class SortableContainer extends Component {
    static template = xml`<t t-call-slot="default"/>`;

    props = props({
        setupLayoutEffect: t.function(),
    });

    setup() {
        this.props.setupLayoutEffect();
    }
}

export class BuilderList extends Component {
    static template = "html_builder.BuilderList";
    static components = { BuilderComponent, SortableContainer, SelectMenu };

    props = props({
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),

        action: t.string().optional(),
        actionParam: t.any().optional(),

        // Shorthand actions.
        classAction: t.any().optional(),
        attributeAction: t.any().optional(),
        dataAttributeAction: t.any().optional(),
        styleAction: t.any().optional(),

        id: t.string().optional(),
        addItemTitle: t.string().optional(_t("Add")),
        itemShape: t
            .customValidator(
                t.record(t.selection(["number", "text", "boolean", "exclusive_boolean"])),
                (value) =>
                    // is not empty object and doesn't include reserved fields
                    Object.keys(value).length > 0 && !Object.keys(value).includes("_id")
            )
            .optional({ value: "text" }),
        default: t.any().optional(),
        sortable: t.any().optional(true),
        hiddenProperties: t.array().optional([]),
        records: t.string().optional(),
        defaultNewValue: t.object().optional({}),
        columnWidth: t.any().optional({}),
        forbidLastItemRemoval: t.boolean().optional(false),
        isEditable: t.boolean().optional(true),
        limit: t.number().optional(50),
        disableLastCheckedCheckbox: t.boolean().optional(false),
        withScrollbar: t.boolean().optional(true),
    });

    setup() {
        if (this.props.default) {
            this.validateProps();
        }
        this.dialog = useService("dialog");
        useBuilderComponent();
        useAutoFocusNewItem("table");
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.parseDisplayValue([]),
            parseDisplayValue: this.parseDisplayValue,
            formatRawValue: this.formatRawValue.bind(this),
        });
        this.state = state;
        this.commit = commit;
        this.preview = preview;
        this.tableRef = useRef("table");
        this.visibilityState = proxy({
            limit: this.props.limit,
        });
        this.onTableScroll = useThrottleForAnimation(this._onTableScroll);
    }

    get allRecords() {
        return this.formatRawValue(this.props.records);
    }

    get cappedItems() {
        return this.getIncludedRecords().slice(0, this.visibilityState.limit);
    }

    get hasMoreItems() {
        return this.cappedItems.length < this.getIncludedRecords().length;
    }

    setupSortable() {
        if (this.props.sortable) {
            useSortable({
                enable: () => this.props.sortable,
                ref: this.tableRef,
                elements: ".o_row_draggable",
                handle: ".o_handle_cell",
                cursor: "grabbing",
                placeholderClasses: ["d-table-row"],
                onDrop: (params) => {
                    const { element, previous } = params;
                    this.reorderItem(element.dataset.id, previous?.dataset.id);
                },
            });
        }
    }

    loadMoreItems() {
        if (!this.hasMoreItems) {
            return;
        }
        this.visibilityState.limit = Math.min(
            this.visibilityState.limit + this.props.limit,
            this.getIncludedRecords().length
        );
    }

    _onTableScroll(ev) {
        const tableWrapperEl = ev.currentTarget;
        const distanceToBottom =
            tableWrapperEl.scrollHeight - (tableWrapperEl.scrollTop + tableWrapperEl.clientHeight);
        if (distanceToBottom <= 100) {
            this.loadMoreItems();
        }
    }

    validateProps() {
        // keys match
        const itemShapeKeys = Object.keys(this.props.itemShape);
        const defaultKeys = Object.keys(this.props.default);
        const allKeys = new Set([...itemShapeKeys, ...defaultKeys]);
        if (allKeys.size !== itemShapeKeys.length) {
            throw new Error("default properties don't match itemShape");
        }
    }

    getIncludedRecords() {
        return this.formatRawValue(this.state.value);
    }

    getExcludedRecords() {
        const itemIds = new Set(this.getIncludedRecords().map((r) => r.id));
        return this.allRecords.filter((record) => record.id && !itemIds.has(record.id));
    }

    openRecordsDialog() {
        this.dialog.add(BuilderListDialog, {
            excludedRecords: this.getExcludedRecords(),
            includedRecords: this.getIncludedRecords(),
            save: this.commit,
        });
    }

    parseDisplayValue(displayValue) {
        return JSON.stringify(displayValue);
    }

    formatRawValue(rawValue) {
        const items = rawValue ? JSON.parse(rawValue) : [];
        let nextAvailableId = items ? this.getNextAvailableItemId(items) : 0;
        for (const item of items) {
            if (!("_id" in item)) {
                item._id = nextAvailableId.toString();
                nextAvailableId += 1;
            }
        }
        return items;
    }

    addItem(record) {
        const items = this.getIncludedRecords();
        items.push(record ?? this.makeDefaultItem());
        this.commit(items);
    }

    updateRecords() {
        const selectedRecordsMap = new Map(
            this.getIncludedRecords()
                .filter((r) => r.id)
                .map((r) => [r.id, r])
        );
        const newRecords = this.allRecords
            .map((record) => selectedRecordsMap.get(record.id) || record)
            .sort((a, b) => localeCompare(a.display_name, b.display_name));
        this.commit(newRecords);
    }

    removeAllItems() {
        this.commit([]);
    }

    deleteItem(itemId) {
        const items = this.getIncludedRecords();
        this.commit(items.filter((item) => item._id !== itemId));
    }

    reorderItem(itemId, previousId) {
        let items = this.getIncludedRecords();
        const itemToReorder = items.find((item) => item._id === itemId);
        items = items.filter((item) => item._id !== itemId);

        const previousItem = items.find((item) => item._id === previousId);
        const previousItems = items.slice(0, items.indexOf(previousItem) + 1);

        const nextItems = items.slice(items.indexOf(previousItem) + 1, items.length);

        const newItems = [...previousItems, itemToReorder, ...nextItems];
        this.commit(newItems);
    }

    makeDefaultItem() {
        return {
            ...this.props.defaultNewValue,
            ...this.props.default,
            _id: this.getNextAvailableItemId().toString(),
        };
    }

    getNextAvailableItemId(items) {
        items = items || this.formatRawValue(this.state?.value);
        const biggestId = items
            .map((item) => parseInt(item._id))
            .reduce((acc, id) => (id > acc ? id : acc), -1);
        const nextAvailableId = biggestId + 1;
        return nextAvailableId;
    }

    onInput(e) {
        this.handleValueChange(e.target, false);
    }

    onChange(e) {
        this.handleValueChange(e.target, true);
    }

    handleValueChange(targetInputEl, commitToHistory) {
        const id = targetInputEl.dataset.id;
        const propertyName = targetInputEl.name;
        const isCheckbox = targetInputEl.type === "checkbox";
        const isText = targetInputEl.type === "text";
        const value = isCheckbox ? targetInputEl.checked : targetInputEl.value;

        let items = this.formatRawValue(this.state.value);

        if (value === true && this.props.itemShape[propertyName] === "exclusive_boolean") {
            for (const item of items) {
                item[propertyName] = false;
            }
        }
        const item = items.find((item) => item._id === id);
        item[propertyName] = value;
        if (!isCheckbox) {
            item.id = isSmallInteger(value) ? parseInt(value) : value;
        }

        // Empty text inputs are not allowed, so we remove them, unless removing
        // them would violate `props.forbidLastItemRemoval`.
        const inputIsEmptyText = isText && value === "";
        const canDeleteItem = items.length > 1 || !this.props.forbidLastItemRemoval;
        if (inputIsEmptyText && canDeleteItem) {
            items = items.filter((item) => item._id !== id);
        }

        if (commitToHistory) {
            this.commit(items);
        } else {
            this.preview(items);
        }
    }

    /**
     * Checks if the checkbox for the given item is the only one
     * still checked for the given property, and should be disabled
     * to prevent unchecking all options.
     *
     * @param {Array} items - List of all items
     * @param {Object} currentItem - Item to check
     * @param {string} propertyName - Property name to check against
     * @returns {boolean} True if this is the last checked checkbox
     */
    isLastCheckboxChecked(items, currentItem, propertyName) {
        if (!this.props.disableLastCheckedCheckbox || !currentItem[propertyName]) {
            return false;
        }
        let activeCount = 0;
        for (const item of items) {
            if (item[propertyName]) {
                activeCount++;
            }
            if (activeCount > 1) {
                return false;
            }
        }
        return true;
    }
}
