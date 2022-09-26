/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';

export class SaleOrderLineProductField extends Many2OneField {

    setup() {
        super.setup();
        const { update } = this;
        this.update = async (value) => {
            const record = await update(value);
            if (!this.props.value || this.props.value[0] !== record[this.props.name][0]) {
                if (this.props.relation === 'product.template') {
                    this._onProductTemplateUpdate();
                } else {
                    this._onProductUpdate();
                }
            }
        };
    }

    get hasConfigurationButton() {
        return this.isConfigurableLine || this.isConfigurableTemplate;
    }
    get isConfigurableLine() { return false; }
    get isConfigurableTemplate() { return false; }

    get configurationButtonHelp() {
        return this.env._t("Edit Configuration");
    }

    get configurationButtonIcon() {
        return 'btn btn-secondary fa ' + this.configurationButtonFAIcon();
    }

    configurationButtonFAIcon() {
        return 'fa-pencil';
    }

    async _onProductTemplateUpdate() { }
    async _onProductUpdate() { } // event_booth_sale, event_sale, sale_renting

    onEditConfiguration() {
        if (this.isConfigurableLine) {
            this._editLineConfiguration();
        } else {
            this._editProductConfiguration();
        }
    }
    _editLineConfiguration() { } // event_booth_sale, event_sale, sale_renting
    _editProductConfiguration() { } // sale_product_configurator, sale_product_matrix

}

SaleOrderLineProductField.template = "sale.SaleProductField";

registry.category("fields").add("sol_product_many2one", SaleOrderLineProductField);
