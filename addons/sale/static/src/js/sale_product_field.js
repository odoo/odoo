/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';

const { onWillUpdateProps } = owl;


export class SaleOrderLineProductField extends Many2OneField {

    setup() {
        super.setup();
        // TODO see with SAD for a better hook to catch field updates
        // TODO how to trigger updates on all lines/parent record (matrix)
        // TODO how to trigger the _onProductUpdate only once
        //      either when both columns are shown, or when only one is...
        //      product_template_id widget should only trigger _onProductUpdate
        //      if product_id widget isn't instantiated...

        onWillUpdateProps(async (nextProps) => {
            if (nextProps.record.mode === 'edit' && nextProps.value) {
                if (
                    !this.props.value ||
                    this.props.value[0] != nextProps.value[0]
                ) {
                    // Field was updated if line was open in edit mode,
                    //      field is not emptied,
                    //      new value is different than existing value.

                    if (this.props.relation == 'product.template') {
                        this._onProductTemplateUpdate();
                    } else {
                        this._onProductUpdate();
                    }
                } else if (this.productConfigured) {
                    // FIXME productConfigured = temp solution
                    //      we need a safe way to link configurators logic
                    //      even if both template & variant columns are enabled
                    this.productConfigured = false;
                    this._onProductUpdate();
                }
            }
        });
    }

    get hasConfigurationButton() {
        return this.isConfigurableLine || this.isConfigurableTemplate;
    }

    get configurationButtonHelp() {
        return this.env._t("Edit Configuration");
    }

    get ConfigurationButtonIcon() {
        return 'btn btn-secondary fa fa-pencil';
    }

    async _onProductTemplateUpdate() {}
    async _onProductUpdate() { }

    onEditConfiguration() {
        if (this.isConfigurableLine) {
            this._editLineConfiguration();
        } else {
            this._editProductConfiguration();
        }
    }
    _editLineConfiguration() { } // event_sale, sale_renting
    _editProductConfiguration() { } // sale_product_configurator, sale_product_matrix

    get isConfigurableLine() { return false; }
    get isConfigurableTemplate() { return false; }
}

SaleOrderLineProductField.template = "sale.SaleProductField";

registry.category("fields").add("sol_product_many2one", SaleOrderLineProductField);
