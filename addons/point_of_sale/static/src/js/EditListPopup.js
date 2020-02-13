odoo.define('point_of_sale.EditListPopup', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const { popupsRegistry } = require('point_of_sale.popupsRegistry');
    const { InputPopup } = require('point_of_sale.AbstractPopups');
    const { EditListInput } = require('point_of_sale.EditListInput');

    /**
     * Given a array of { id, text }, we show the user this popup to be able to modify this given array.
     * (used to replace PackLotLinePopupWidget)
     *
     * The expected return of this popup when used with showPopup is an array of { _id, [id], text }.
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
     *   // when user pressed okay in the popup, the changes he made will be returned by the showPopup function.
     *   const { agreed: isUserAgreed, data: newNames } = await this.showPopup('EditListPopup', {
     *     title: "Are you okay with this item?",
     *     array: names })
     *
     *   // we then consume the new data. In this example, it is only logged.
     *   if (isUserAgreed) {
     *     console.log(newNames);
     *     // the above might log the following:
     *     // [{ _id: 1, id: 1, text: 'Joseph Caburnay' }, { _id: 2, id: 2, 'Kaykay' }, { _id: 3, 'James' }]
     *     // The result showed that the original item with id=1 was changed to have text 'Joseph Caburnay' from 'Joseph'
     *     // The one with id=2 did not change. And a new item with text='James' is added.
     *   }
     * ```
     */
    class EditListPopup extends InputPopup {
        /**
         * @param {String} title required title of popup
         * @param {Array} [props.array=[]] the array of { id, text } to be edited
         * @param {Boolean} [props.isSingleItem=false] true if only allowed to edit single item (the first item)
         */
        constructor() {
            super(...arguments);
            this._id = 0;
            this.state = useState({ array: this._initialize(this.props.array) });
        }
        _nextId() {
            return this._id++;
        }
        _emptyItem() {
            return {
                text: '',
                _id: this._nextId(),
            };
        }
        _initialize(array) {
            // If no array is provided, we initialize with one empty item.
            if (array.length === 0) return [this._emptyItem()];
            // Put _id for each item. It will serve as unique identifier of each item.
            return array.map(item => ({ _id: this._nextId(), ...item }));
        }
        removeItem(event) {
            const itemToRemove = event.detail;
            this.state.array.splice(
                this.state.array.findIndex(item => item.id == itemToRemove.id),
                1
            );
            // We keep a minimum of one empty item in the popup.
            if (this.state.array.length === 0) {
                this.state.array.push(this._emptyItem());
            }
        }
        createNewItem() {
            if (this.props.isSingleItem) return;
            this.state.array.push(this._emptyItem());
        }
        /**
         * @override
         */
        async setupData() {
            await super.setupData(...arguments);
            this.data = {
                array: this.getStateTarget(this.state).array,
            };
        }
    }
    EditListPopup.components = { EditListInput };
    EditListPopup.defaultProps = {
        array: [],
        isSingleItem: false,
    };

    popupsRegistry.add(EditListPopup);

    return { EditListPopup };
});
