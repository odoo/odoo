/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';

export class SaleOrderLineProductField extends Many2OneField {

    setup() {
        super.setup();
        const { update } = this;
        this.update = async (value) => {
            await update(value);
            let newValue = false;
            // NB: quick creation doesn't go through here, but through quickCreate
            // below
            if (value) {
                if (Array.isArray(value[0]) && this.props.value != value[0]) {
                    // product (existing)
                    newValue = true;
                } else {
                    // new product (Create & edit)
                    // value[0] is a dict of creation values
                    newValue = true;
                }
            }
            if (newValue) {
                if (this.props.relation === 'product.template') {
                    this._onProductTemplateUpdate();
                } else {
                    this._onProductUpdate();
                }
            }
        };

        if (this.props.canQuickCreate) {
            // HACK to make quick creation also open
            //      configurators if needed
            this.quickCreate = async (name, params = {}) => {
                await this.props.record.update({ [this.props.name]: [false, name]});

                if (this.props.relation === 'product.template') {
                    this._onProductTemplateUpdate();
                } else {
                    this._onProductUpdate();
                }
            };
        }
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
