import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import { BuilderListDialog } from "@html_builder/core/building_blocks/builder_list_dialog";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "@html_builder/core/utils";
import { isSmallInteger } from "@html_builder/utils/utils";
import { Component, onWillUpdateProps, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useSortable } from "@web/core/utils/sortable_owl";
import { useService } from "@web/core/utils/hooks";

export class BuilderList extends Component {
    static template = "html_builder.BuilderList";
    static props = {
        ...basicContainerBuilderComponentProps,
        id: { type: String, optional: true },
        addItemTitle: { type: String, optional: true },
        itemShape: {
            type: Object,
            values: [
                { value: "number" },
                { value: "text" },
                { value: "boolean" },
                { value: "exclusive_boolean" },
            ],
            validate: (value) =>
                // is not empty object and doesn't include reserved fields
                Object.keys(value).length > 0 && !Object.keys(value).includes("_id"),
            optional: true,
        },
        default: { optional: true },
        sortable: { optional: true },
        hiddenProperties: { type: Array, optional: true },
        records: { type: String, optional: true },
        defaultNewValue: { type: Object, optional: true },
        columnWidth: { optional: true },
        forbidLastItemRemoval: { type: Boolean, optional: true },
    };
    static defaultProps = {
        addItemTitle: _t("Add"),
        itemShape: { value: "text" },
        default: { value: _t("Item") },
        sortable: true,
        hiddenProperties: [],
        mode: "button",
        defaultNewValue: {},
        columnWidth: {},
        forbidLastItemRemoval: false,
    };
    static components = { BuilderComponent, SelectMenu };

    setup() {
        this.validateProps();
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

        onWillUpdateProps((props) => {
            this.allRecords = this.formatRawValue(props.records);
        });

        if (this.props.sortable) {
            useSortable({
                enable: () => this.props.sortable,
                ref: useRef("table"),
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
        const value = isCheckbox ? targetInputEl.checked : targetInputEl.value;

        const items = this.formatRawValue(this.state.value);
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

        if (commitToHistory) {
            this.commit(items);
        } else {
            this.preview(items);
        }
    }
}
