import { Dialog } from "@web/core/dialog/dialog";
import { useSortable } from "@web/core/utils/sortable_owl";

import { Component, useRef, useState } from "@odoo/owl";

export class SelectionContentDialog extends Component {
    static components = {
        Dialog,
    };
    static defaultProps = {
        defaultChoices: [],
    };
    static props = {
        defaultChoices: { type: Array, optional: true },
        onConfirm: { type: Function },
        close: { type: Function },
    };
    static template = "web_studio.SelectionContentDialog";

    setup() {
        this.state = useState({
            choices: this.props.defaultChoices,
        });
        this.localState = useState({
            _newItem: [],
            editedItem: null,
        });

        const itemsList = useRef("itemsList");
        useSortable({
            enable: () => !this.editedItem,
            handle: ".o-draggable-handle",
            ref: itemsList,
            elements: ".o-draggable",
            cursor: "move",
            onDrop: (params) => this.resequenceItems(params),
        });

        this.oldValue = new WeakMap();
    }

    getSelectionFromItem(item) {
        if (item.id === "new") {
            return this.localState._newItem;
        }
        return this.selection[item.id];
    }

    get selection() {
        return this.state.choices;
    }

    set selection(items) {
        this.state.choices = items;
    }

    selectionToItem(selection, params = {}) {
        return Object.assign(
            {
                id: "new",
                key: selection[0],
                name: selection[0],
                label: selection[1],
                isDraggable: false,
                isRemovable: false,
                isInEdition: false,
            },
            params
        );
    }

    get selectionToItems() {
        const inEdition = !!this.editedItem;
        return this.selection.map((sel, index) => {
            return this.selectionToItem(sel, {
                id: index,
                key: inEdition ? index : sel[0],
                isInEdition:
                    this.editedItem?.id === this.selection.indexOf(sel) && !this.shouldFullEdit,
                isDraggable: !inEdition,
                isRemovable: !inEdition,
            });
        });
    }

    get newItem() {
        return this.selectionToItem(this.localState._newItem, { isInEdition: true, id: "new" });
    }

    get editedItem() {
        return this.localState.editedItem;
    }

    get shouldFullEdit() {
        return Boolean(this.env.debug);
    }

    ensureUnique(item) {
        const value = item[0];
        if (!value) {
            return false;
        }

        const otherElements = this.selection.filter((i) => i !== item);
        if (otherElements.some((i) => i[0] === value)) {
            return false;
        }
        return true;
    }

    setItemValue(item, value) {
        if (item.id !== "new" && item.id !== this.editedItem.id) {
            return;
        }
        const isEditingLabel = item.id !== "new";
        item = this.getSelectionFromItem(item);
        item[0] = isEditingLabel ? this.editedItem.name : value;
        item[1] = value;
    }

    addItem(item) {
        if (!this.ensureUnique(item)) {
            return;
        }
        this.selection.push(item);
        this.localState._newItem = [];
    }

    removeItem(item) {
        this.selection = this.selection.filter((i) => i[0] !== item.name);
    }

    editItem(item) {
        const selItem = this.getSelectionFromItem(item);
        if (item.id === "new") {
            selItem[0] = selItem[0]?.trim();
            selItem[1] = selItem[1]?.trim();
            return this.addItem(selItem);
        }
        if (this.editedItem?.id === item.id) {
            const old = this.oldValue.get(selItem);
            if (old[0] !== selItem[0]) {
                selItem[0] = selItem[0]?.trim();
            }
            if (old[1] !== selItem[1]) {
                selItem[1] = selItem[1]?.trim();
            }
            if (!this.ensureUnique(selItem)) {
                return;
            }
            this.localState.editedItem = null;
            this.oldValue.delete(selItem);
            return;
        }
        this.oldValue.set(selItem, [...selItem]);
        this.localState.editedItem = item;
    }

    discardItemChanges(item) {
        if (item.id === "new") {
            return this.setItemValue(item, "");
        }
        const selItem = this.getSelectionFromItem(item);
        const oldValue = this.oldValue.get(selItem);
        selItem[0] = oldValue[0];
        selItem[1] = oldValue[1];
        this.localState.editedItem = null;
    }

    resequenceItems(params) {
        const { previous, next, element } = params;
        const itemId = parseInt(element.dataset.itemId);

        let items = this.selection;
        const item = items[itemId];
        items = items.filter((i) => i !== item);

        let toIndex;
        if (previous) {
            toIndex = parseInt(previous.dataset.itemId) + 1;
        } else if (next) {
            toIndex = parseInt(next.dataset.itemId);
        }
        items.splice(toIndex, 0, item);
        this.selection = items;
    }

    async onConfirm() {
        if (this.newItem.name?.length) {
            this.editItem(this.newItem);
        }
        await this.props.onConfirm(this.selection);
        this.props.close();
    }

    onKeyPressed(item, key) {
        if (key === "Enter") {
            this.editItem(item);
        }
    }
}
