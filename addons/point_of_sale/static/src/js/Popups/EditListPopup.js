/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { useAutoFocusToLast } from "@point_of_sale/js/custom_hooks";
import { _lt } from "@web/core/l10n/translation";

const { useState } = owl;

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
 *   // when user pressed `confirm` in the popup, the changes he made will be returned by the showPopup function.
 *   const { confirmed, payload: newNames } = await this.showPopup('EditListPopup', {
 *     title: "Can you confirm this item?",
 *     array: names })
 *
 *   // we then consume the new data. In this example, it is only logged.
 *   if (confirmed) {
 *     console.log(newNames);
 *     // the above might log the following:
 *     // [{ _id: 1, id: 1, text: 'Joseph Caburnay' }, { _id: 2, id: 2, 'Kaykay' }, { _id: 3, 'James' }]
 *     // The result showed that the original item with id=1 was changed to have text 'Joseph Caburnay' from 'Joseph'
 *     // The one with id=2 did not change. And a new item with text='James' is added.
 *   }
 * ```
 */
class EditListPopup extends AbstractAwaitablePopup {
    /**
     * @param {String} title required title of popup
     * @param {Array} [props.array=[]] the array of { id, text } to be edited or an array of strings
     * @param {Boolean} [props.isSingleItem=false] true if only allowed to edit single item (the first item)
     */
    setup() {
        super.setup();
        this._id = 0;
        this.state = useState({ array: this._initialize(this.props.array) });
        useAutoFocusToLast();
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
    onInputChange(itemId, text) {
        const item = this.state.array.find((elem) => elem._id === itemId);
        item.text = text;
    }
    createNewItem() {
        if (this.props.isSingleItem) {
            return;
        }
        this.state.array.push(this._emptyItem());
    }
    /**
     * @override
     */
    getPayload() {
        return {
            newArray: this.state.array
                .filter((item) => item.text.trim() !== "")
                .map((item) => Object.assign({}, item)),
        };
    }
}
EditListPopup.template = "EditListPopup";
EditListPopup.defaultProps = {
    confirmText: _lt("Add"),
    cancelText: _lt("Discard"),
    array: [],
    isSingleItem: false,
};

Registries.Component.add(EditListPopup);

export default EditListPopup;
