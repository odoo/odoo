import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "@html_builder/core/utils";
import { Component, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useSortable } from "@web/core/utils/sortable_owl";

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
    };
    static defaultProps = {
        addItemTitle: _t("Add"),
        itemShape: { value: "text" },
        default: { value: _t("Item") },
        sortable: true,
        hiddenProperties: [],
    };
    static components = { BuilderComponent };

    setup() {
        this.validateProps();

        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.parseDisplayValue([]),
            parseDisplayValue: this.parseDisplayValue,
            formatRawValue: this.formatRawValue,
        });
        this.state = state;
        this.commit = commit;
        this.preview = preview;

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

    parseDisplayValue(displayValue) {
        return JSON.stringify(displayValue);
    }

    formatRawValue(rawValue) {
        const items = rawValue ? JSON.parse(rawValue) : [];
        for (const item of items) {
            if (!("_id" in item)) {
                item._id = this.getNextAvailableItemId(items);
            }
        }
        return items;
    }

    addItem() {
        const items = this.formatRawValue(this.state.value);
        items.push(this.makeDefaultItem());
        this.commit(items);
    }

    deleteItem(itemId) {
        const items = this.formatRawValue(this.state.value);
        this.commit(items.filter((item) => item._id !== itemId));
    }

    reorderItem(itemId, previousId) {
        let items = this.formatRawValue(this.state.value);
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
            ...this.props.default,
            _id: this.getNextAvailableItemId(),
        };
    }

    getNextAvailableItemId(items) {
        items = items || this.formatRawValue(this.state?.value);
        const biggestId = items
            .map((item) => parseInt(item._id))
            .reduce((acc, id) => (id > acc ? id : acc), -1);
        const nextAvailableId = biggestId + 1;
        return nextAvailableId.toString();
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
        const value =
            targetInputEl.type === "checkbox" ? targetInputEl.checked : targetInputEl.value;

        const items = this.formatRawValue(this.state.value);
        if (value === true && this.props.itemShape[propertyName] === "exclusive_boolean") {
            for (const item of items) {
                item[propertyName] = false;
            }
        }
        const item = items.find((item) => item._id === id);
        item[propertyName] = value;

        if (commitToHistory) {
            this.commit(items);
        } else {
            this.preview(items);
        }
    }
}
