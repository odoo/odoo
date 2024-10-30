import { Dialog } from '@web/core/dialog/dialog';
import { formatMonetary } from "@web/views/fields/formatters";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { Component, onMounted, markup, useRef } from "@odoo/owl";

export class ProductMatrixDialog extends Component {
    static template = "product_matrix.dialog";
    static props = {
        header: { type: Object },
        rows: { type: Object },
        editedCellAttributes: { type: String },
        product_template_id: { type: Number },
        record: { type: Object },
        close: { type: Function },
    };
    static components = { Dialog };

    setup() {
        this.size = 'xl';

        const productMatrixRef = useRef('productMatrix');
        useHotkey("enter", () => this._onConfirm(), {
            /***
             * By default, Hotkeys don't work in input fields. As the matrix table is composed of
             * input fields, the `bypassEditableProtection` param will allow Hotkeys to work from
             * the input fields.
             *
             * To avoid triggering the confirmation when pressing 'enter' on the close or the
             * discard button, we only set the hotkey area on the matrix table.
             */
            bypassEditableProtection: true,
            area: () => productMatrixRef.el,
        });

        onMounted(() => {
            if(this.props.editedCellAttributes.length) {
                const inputs = document.getElementsByClassName('o_matrix_input');
                Array.from(inputs).filter((matrixInput) =>
                    matrixInput.attributes.ptav_ids.nodeValue === this.props.editedCellAttributes
                )[0].select();
            } else {
                document.getElementsByClassName('o_matrix_input')[0].select();
            }
        });
    }

    _format({price, currency_id}) {
        if (!price) { return ""; }
        const sign = price < 0 ? '-' : '+';
        const formatted = formatMonetary(
            Math.abs(price),
            {
                currencyId: currency_id,
            },
        );
        return markup(`&nbsp;${sign}&nbsp;${formatted}&nbsp;`);
    }

    _onConfirm() {
        const inputs = document.getElementsByClassName('o_matrix_input');
        let matrixChanges = [];
        for (let matrixInput of inputs) {
            if (matrixInput.value && matrixInput.value !== matrixInput.attributes.value.nodeValue) {
                matrixChanges.push({
                    qty: parseFloat(matrixInput.value),
                    ptav_ids: matrixInput.attributes.ptav_ids.nodeValue.split(",").map(
                        id => parseInt(id)
                    ),
                });
            }
        }
        if (matrixChanges.length > 0) {
            // NB: server also removes current line opening the matrix
            this.props.record.update({
                grid: JSON.stringify({
                    changes: matrixChanges,
                    product_template_id: this.props.product_template_id
                }),
                grid_update: true // to say that the changes to grid have to be applied to the SO.
            });
        }
        this.props.close();
    }
}
