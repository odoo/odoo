/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class Digipad extends Component {
    setup() {
        this.orm = useService('orm');
        const user = useService('user');
        this.buttons = [7, 8, 9, 4, 5, 6, 1, 2, 3, '.', '0', 'erase'].map((value, index) => {
            return { index, value };
        });
        this.value = String(this.props.record.data[this.props.quantityField]);
        onWillStart(async () => {
            this.displayUOM = await user.hasGroup('uom.group_uom');
            await this._fetchPackagingButtons();
        });
    }

    get changes() {
        return { [this.props.quantityField]: Number(this.value) };
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Copies the input value if digipad value is not set yet, or overrides it if there is a
     * difference between the two values (in case user has manualy edited the input value).
     * @private
     */
    _checkInputValue() {
        const input = document.querySelector(`div[name="${this.props.quantityField}"] input`);
        const inputValue = input.value;
        if (Number(this.value) != Number(inputValue)) {
            console.warn(`-- Change widget value: ${this.value} -> ${inputValue}`);
            this.value = inputValue;
        }
    }

    /**
     * Increments the field value by the interval amount (1 by default).
     * @private
     * @param {integer} [interval=1]
     */
    async _increment(interval=1) {
        this._checkInputValue();
        const fraction = this.value.split('.')[1]
        const numberValue = Number(this.value || 0);
        this.value = (numberValue + interval).toFixed(fraction?.length);
        await this.props.record.update(this.changes);
    }

    /**
     * Search for the product's packaging buttons.
     * @private
     * @returns {Promise}
     */
    async _fetchPackagingButtons() {
        const record = this.props.record.data;
        const demandQty = record.quantity;
        const domain = [['product_id', '=', record.product_id[0]]];
        if (demandQty) { // Doesn't fetch packaging with a too high quantity.
            domain.push(['qty', '<=', demandQty]);
        }
        this.packageButtons = await this.orm.searchRead(
            'product.packaging',
            domain,
            ['name', 'product_uom_id', 'qty'],
            { limit: 3 },
        );
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the click on one of the digipad's button and updates the value..
     * @private
     * @param {String} button
     */
    _onCLickButton(button) {
        this._checkInputValue();
        if (button === 'erase') {
            this.value = this.value.substr(0, this.value.length - 1);
        } else {
            if (button === '.' && this.value.indexOf('.') != -1) {
                // Avoids to add a decimal separator multiple time.
                return;
            }
            this.value += button;
        }
        this.props.record.update(this.changes);
    }
}
Digipad.template = 'stock_barcode.DigipadTemplate';
Digipad.props = {
    ...standardWidgetProps,
    quantityField: { type: String }
};

export const digipad = {
    component: Digipad,
    extractProps: ({ attrs }) => {
        return {
            quantityField: attrs.quantity_field,
        };
    },
};
registry.category('view_widgets').add('digipad', digipad);
