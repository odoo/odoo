/** @odoo-module **/

import Dialog from 'web.Dialog';
import { qweb } from "web.core";
import { patch } from "@web/core/utils/patch";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { formatMonetary } from "@web/views/fields/formatters";
const { markup } = owl;


patch(SaleOrderLineProductField.prototype, 'sale_product_matrix', {

    async _openGridConfigurator(mode) {
        const saleOrderRecord = this.props.record.model.root;

        // fetch matrix information from server;
        await saleOrderRecord.update({
            grid_product_tmpl_id: this.props.record.data.product_template_id,
        });

        let updatedLineAttributes = [];
        if (mode === 'edit') {
            // provide attributes of edited line to automatically focus on matching cell in the matrix
            for (let ptnvav of this.props.record.data.product_no_variant_attribute_value_ids.records) {
                updatedLineAttributes.push(ptnvav.data.id);
            }
            for (let ptav of this.props.record.data.product_template_attribute_value_ids.records) {
                updatedLineAttributes.push(ptav.data.id);
            }
            updatedLineAttributes.sort((a, b) => { return a - b; });
        }

        this._openMatrixConfigurator(
            saleOrderRecord.data.grid,
            this.props.record.data.product_template_id[0],
            updatedLineAttributes,
        );

        if (mode !== 'edit') {
            // remove new line used to open the matrix
            saleOrderRecord.data.order_line.removeRecord(this.props.record);
        }
    },

    async _openProductConfigurator(mode) {
        if (mode === 'edit' && this.props.record.data.product_add_mode == 'matrix') {
            this._openGridConfigurator('edit');
        } else {
            this._super(...arguments);
        }
    },

    /**
     * Triggers Matrix Dialog opening
     *
     * @param {String} jsonInfo matrix dialog content
     * @param {integer} productTemplateId product.template id
     * @param {editedCellAttributes} list of product.template.attribute.value ids
     *  used to focus on the matrix cell representing the edited line.
     *
     * @private
    */
     _openMatrixConfigurator: function (jsonInfo, productTemplateId, editedCellAttributes) {
        const infos = JSON.parse(jsonInfo);
        const saleOrderRecord = this.props.record.model.root;
        const MatrixDialog = new Dialog(this, {
            title: this.env._t('Choose Product Variants'),
            size: 'extra-large', // adapt size depending on matrix size?
            $content: $(qweb.render(
                'product_matrix.matrix', {
                    header: infos.header,
                    rows: infos.matrix,
                    format({price, currency_id}) {
                        if (!price) { return ""; }
                        const sign = price < 0 ? '-' : '+';
                        const formatted = formatMonetary(
                            Math.abs(price),
                            {
                                currencyId: currency_id,
                            },
                        );
                        return markup(`${sign}&nbsp;${formatted}`);
                    }
                }
            )),
            buttons: [
                {text: this.env._t('Confirm'), classes: 'btn-primary', close: true, click: function (result) {
                    const $inputs = this.$('.o_matrix_input');
                    var matrixChanges = [];
                    _.each($inputs, function (matrixInput) {
                        if (matrixInput.value && matrixInput.value !== matrixInput.attributes.value.nodeValue) {
                            matrixChanges.push({
                                qty: parseFloat(matrixInput.value),
                                ptav_ids: matrixInput.attributes.ptav_ids.nodeValue.split(",").map(function (id) {
                                      return parseInt(id);
                                }),
                            });
                        }
                    });
                    if (matrixChanges.length > 0) {
                        // NB: server also removes current line opening the matrix
                        saleOrderRecord.update({
                            grid: JSON.stringify({changes: matrixChanges, product_template_id: productTemplateId}),
                            grid_update: true // to say that the changes to grid have to be applied to the SO.
                        });
                    }
                }},
                {text: this.env._t('Close'), close: true},
            ],
        }).open();

        MatrixDialog.opened(function () {
            MatrixDialog.$content.closest('.o_dialog_container').removeClass('d-none');
            if (editedCellAttributes.length > 0) {
                const str = editedCellAttributes.toString();
                MatrixDialog.$content.find('.o_matrix_input').filter((k, v) => v.attributes.ptav_ids.nodeValue === str)[0].focus();
            } else {
                MatrixDialog.$content.find('.o_matrix_input:first()').focus();
            }
        });
    },
});
