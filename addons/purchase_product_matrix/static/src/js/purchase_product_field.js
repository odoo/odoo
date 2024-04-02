/** @odoo-module **/

import Dialog from 'web.Dialog';
import { qweb } from "web.core";
import { registry } from '@web/core/registry';
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';
import { formatMonetary } from "@web/views/fields/formatters";
import { useEffect } from '@odoo/owl';

const { markup } = owl;


export class PurchaseOrderLineProductField extends Many2OneField {

    setup() {
        super.setup();
        let isMounted = false;
        let isInternalUpdate = false;
        const super_update = this.update;
        this.update = (recordlist) => {
            isInternalUpdate = true;
            super_update(recordlist);
        };
        if (this.props.canQuickCreate) {
            this.quickCreate = (name, params = {}) => {
                if (params.triggeredOnBlur) {
                    return this.openConfirmationDialog(name);
                }
                isInternalUpdate = true;
                return this.props.update([false, name]);
            };
        }
        useEffect(value => {
            if (!isMounted) {
                isMounted = true;
            } else if (value && isInternalUpdate) {
                // we don't want to trigger product update when update comes from an external sources,
                // such as an onchange, or the product configuration dialog itself
                this._onProductTemplateUpdate();
            }
            isInternalUpdate = false;
        }, () => [Array.isArray(this.value) && this.value[0]]);
    }

    get configurationButtonHelp() {
        return this.env._t("Edit Configuration");
    }
    get isConfigurableTemplate() {
        return this.props.record.data.is_configurable_product;
    }

    async _onProductTemplateUpdate() {
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id[0]],
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                this.props.record.update({
                    // TODO right name get (same problem as configurator)
                    product_id: [result.product_id, 'whatever'],
                });
            }
        } else {
            this._openGridConfigurator(false);
        }
    }

    onEditConfiguration() {
        if (this.props.record.data.is_configurable_product) {
            this._openGridConfigurator(true);
        }
    }

    async _openGridConfigurator(edit) {
        const PurchaseOrderRecord = this.props.record.model.root;

        // fetch matrix information from server;
        await PurchaseOrderRecord.update({
            grid_product_tmpl_id: this.props.record.data.product_template_id,
        });

        let updatedLineAttributes = [];
        if (edit) {
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
            PurchaseOrderRecord.data.grid,
            this.props.record.data.product_template_id[0],
            updatedLineAttributes,
        );

        if (!edit) {
            // remove new line used to open the matrix
            PurchaseOrderRecord.data.order_line.removeRecord(this.props.record);
        }
    }

    _openMatrixConfigurator(jsonInfo, productTemplateId, editedCellAttributes) {
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
    }
}

PurchaseOrderLineProductField.template = "purchase.PurchaseProductField";

registry.category("fields").add("pol_product_many2one", PurchaseOrderLineProductField);
