import { Dialog } from "@web/core/dialog/dialog";
import { useAutoFocusToLast } from "@point_of_sale/app/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";
import { EditListInput } from "@point_of_sale/app/store/select_lot_popup/edit_list_input/edit_list_input";

/**
 * Given a array of { id, text }, we show the user this popup to be able to modify this given array.
 * (used to replace PackLotLinePopupWidget)
 *
 * The expected return of showPopup when this popup is used is an array of { _id, [id], text }.
 *   - _id is the assigned unique identifier for each item.
 *   - id is the original id. if not provided, then it means that the item is new.
 *   - text is the modified/unmodified text.
 *
 * Example:
 *
 * ```
 *   -- perhaps inside a click handler --
 *   // gather the items to edit
 *   const names = [{ id: 1, text: 'Joseph'}, { id: 2, text: 'Kaykay' }];
 *
 *   // supply the items to the popup and wait for user's response
 *   this.dialog.add(EditListPopup, {
 *     title: "Can you confirm this item?",
 *     array: names ,
 *     getPayload: (newNames) => console.log(newNames),
 * })
 *     // the above might log the following:
 *     // [{ _id: 1, id: 1, text: 'Joseph Caburnay' }, { _id: 2, id: 2, 'Kaykay' }, { _id: 3, 'James' }]
 *     // The result showed that the original item with id=1 was changed to have text 'Joseph Caburnay' from 'Joseph'
 *     // The one with id=2 did not change. And a new item with text='James' is added.
 *   }
 * ```
 */
export class EditListPopup extends Component {
    static components = { EditListInput, Dialog };
    static template = "point_of_sale.EditListPopup";
    static props = {
        array: Array,
        isSingleItem: Boolean,
        title: String,
        name: String,
        getPayload: Function,
        close: Function,
        options: { type: Array, optional: true },
        customInput: { type: Boolean, optional: true },
        uniqueValues: { type: Boolean, optional: true },
        isLotNameUsed: { type: Function, optional: true },
    };
    static defaultProps = {
        options: [],
        customInput: true,
        uniqueValues: true,
        isLotNameUsed: () => false,
    };

    /**
     * @param {String} title required title of popup
     * @param {Array} [props.array=[]] the array of { id, text } to be edited or an array of strings
     * @param {Boolean} [props.isSingleItem=false] true if only allowed to edit single item (the first item)
     * @param {Array} [props.options=[]] the array of suggested or valid values for the items text
     * @param {Boolean} [props.customInput=true] false to only allow values in props.options for the items text
     * @param {Boolean} [props.uniqueValues=true] true to prevent several items to have the same text value
     */
    setup() {
        this._id = 0;
        this.state = useState({
            array: this._initialize(this.props.array),
            selectedItemId: null,
        });
        useAutoFocusToLast();
        this.editListRef = useRef("edit-list-inputs");
        if (new Set(this.props.options).size !== this.props.options.length) {
            throw new Error("EditListPopup options must be unique.");
        }
    }
    _nextId() {
        return this._id++;
    }
    _emptyItem() {
        return {
            text: "",
            _id: this._nextId(),
        };
    }
    _initialize(array) {
        // If no array is provided, we initialize with one empty item.
        if (array.length === 0) {
            return [this._emptyItem()];
        }
        // Put _id for each item. It will serve as unique identifier of each item.
        return array.map((item) =>
            Object.assign(
                {},
                { _id: this._nextId() },
                typeof item === "object" ? item : { text: item }
            )
        );
    }
    _hasMoreThanOneItem() {
        return this.state.array.length > 1;
    }
    removeItem(itemId) {
        this.state.array.splice(
            this.state.array.findIndex((item) => item._id == itemId),
            1
        );
    }
    getRemainingOptions() {
        const usedValues = new Set(this.state.array.map((e) => e.text));
        return this.props.options.filter((o) => !usedValues.has(o));
    }
    shouldShowOptionsForItem(item) {
        return (
            item._id === this.state.selectedItemId &&
            (this.state.scrolledWithSelectedItemId !== item._id ||
                this.state.scrolledWithSelectedItemValue !== item.text) &&
            (!item.text ||
                !this.props.customInput ||
                !this.hasValidValue(item._id, item.text) ||
                !this.props.options.includes(item.text))
        );
    }
    hasValidValue(itemId, text) {
        return (
            !this.props.isLotNameUsed(text) &&
            (this.props.customInput || this.props.options.includes(text)) &&
            (!this.props.uniqueValues ||
                !this.state.array.some((elem) => elem._id !== itemId && elem.text === text))
        );
    }
    onInputChange(itemId, text) {
        const item = this.state.array.find((elem) => elem._id === itemId);
        item.text = text;
        this.resetScrollInfo();
    }
    onScroll() {
        const listEl = this.editListRef.el;
        if (!listEl) {
            return;
        }
        const curScrollPos = listEl.scrollTop;
        if (
            this.lastScrollPos &&
            curScrollPos !== this.lastScrollPos &&
            this.state.selectedItemId
        ) {
            this.state.scrolledWithSelectedItemId = this.state.selectedItemId;
            const item = this.state.array.find((elem) => elem._id === this.state.selectedItemId);
            this.state.scrolledWithSelectedItemValue = item.text;
        }
        this.lastScrollPos = curScrollPos;
    }
    resetScrollInfo() {
        this.state.scrolledWithSelectedItemId = null;
        this.state.scrolledWithSelectedItemValue = null;
        this.lastScrollPos = null;
    }
    onSelectItem(itemId) {
        this.state.selectedItemId = itemId;
        this.resetScrollInfo();
        if (this.toUnselectItemTimeoutId) {
            clearTimeout(this.toUnselectItemTimeoutId);
        }
    }
    onUnselectItem(itemId) {
        // The unselection must be delayed to allow the user to click on
        // an option of the selected item, otherwise the option disappears
        // before the user click, and the user clicks on nothing.
        this.toUnselectItemTimeoutId = setTimeout(() => {
            if (this.state.selectedItemId === itemId) {
                this.state.selectedItemId = null;
                this.toUnselectItemTimeoutId = null;
                this.resetScrollInfo();
            }
        }, 300);
    }
    createNewItem() {
        if (this.props.isSingleItem) {
            return;
        }
        this.state.array.push(this._emptyItem());
    }
    confirm() {
        const finalValues = new Set();
        this.props.getPayload(
            this.state.array
                .filter((item) => {
                    const itemValue = item.text.trim();
                    const isValidValue =
                        itemValue !== "" &&
                        !this.props.isLotNameUsed(itemValue) &&
                        (this.props.customInput || this.props.options.includes(itemValue));
                    if (!isValidValue) {
                        return false;
                    }
                    if (this.props.uniqueValues) {
                        const isDuplicateValue = finalValues.has(itemValue);
                        if (!isDuplicateValue) {
                            finalValues.add(itemValue);
                        }
                        return !isDuplicateValue;
                    }
                    return true;
                })
                .map((item) => Object.assign({}, item))
        );
        this.props.close();
    }
}
