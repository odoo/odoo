import { useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import { BuilderListDialog } from "@html_builder/core/building_blocks/builder_list_dialog";
import { useBuilderComponent, useInputBuilderComponent } from "@html_builder/core/utils";
import { isSmallInteger } from "@html_builder/utils/utils";
import { Component, onWillUpdateProps, props, types as t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useSortable } from "@web/core/utils/sortable_owl";
import { useService } from "@web/core/utils/hooks";

export class BuilderList extends Component {
    static template = "html_builder.BuilderList";
    static components = { BuilderComponent, SelectMenu };

    props = props(
        {
            "applyTo?": t.string(),
            "preview?": t.boolean(),
            "inheritedActions?": t.array(t.string()),

            "action?": t.string(),
            "actionParam?": t.any(),

            // Shorthand actions.
            "classAction?": t.any(),
            "attributeAction?": t.any(),
            "dataAttributeAction?": t.any(),
            "styleAction?": t.any(),

            "id?": t.string(),
            "addItemTitle?": t.string(),
            "itemShape?": t.customValidator(
                t.record(t.selection(["number", "text", "boolean", "exclusive_boolean"])),
                (value) =>
                    // is not empty object and doesn't include reserved fields
                    Object.keys(value).length > 0 && !Object.keys(value).includes("_id")
            ),
            "default?": t.any(),
            "sortable?": t.any(),
            "hiddenProperties?": t.array(),
            "records?": t.string(),
            "defaultNewValue?": t.object(),
            "columnWidth?": t.any(),
            "forbidLastItemRemoval?": t.boolean(),
            "isEditable?": t.boolean(),
            "limit?": t.number(),
        },
        {
            addItemTitle: _t("Add"),
            itemShape: { value: "text" },
            sortable: true,
            hiddenProperties: [],
            mode: "button",
            defaultNewValue: {},
            columnWidth: {},
            forbidLastItemRemoval: false,
            isEditable: true,
            limit: 50,
        }
    );

    setup() {
        if (this.props.default) {
            this.validateProps();
        }
        this.dialog = useService("dialog");
        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.parseDisplayValue([]),
            parseDisplayValue: this.parseDisplayValue,
            formatRawValue: this.formatRawValue.bind(this),
        });
        this.state = state;
        this.commit = commit;
        this.preview = preview;
        this.allRecords = this.formatRawValue(this.props.records);
        this.visibilityState = useState({
            limit: this.props.limit,
        });
        this.tableRef = useRef("table");
        this.sentinelRef = useRef("sentinel");
        useLayoutEffect(
            () => {
                const sentinelEl = this.sentinelRef.el;
                if (!sentinelEl) {
                    return;
                }
                const observer = new IntersectionObserver(
                    ([entry]) => {
                        if (entry.isIntersecting && this.hasMoreItems) {
                            this.visibilityState.limit += this.props.limit;
                        }
                    },
                    {
                        root: this.tableRef.el.parentElement,
                        threshold: 1.0,
                        rootMargin: "100px",
                    }
                );
                observer.observe(sentinelEl);
                return () => observer.disconnect();
            },
            () => []
        );

        onWillUpdateProps((props) => {
            this.allRecords = this.formatRawValue(props.records);
        });

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

    get cappedItems() {
        return this.getIncludedRecords().slice(0, this.visibilityState.limit);
    }

    get hasMoreItems() {
        return this.cappedItems.length < this.getIncludedRecords().length;
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
            .sort((a, b) => (a.display_name || "").localeCompare(b.display_name || ""));
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
}
