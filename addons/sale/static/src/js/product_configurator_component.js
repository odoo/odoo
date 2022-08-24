/** @odoo-module */

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

const { useState } = owl;

export class ProductConfiguratorField extends Many2OneField {
    setup() {
        super.setup();

        this.state = useState({
            addLinkButton: false,
            addConfigurationButton: false,
        });

        onWillUpdateProps(nextProps => {
            if (this.mode === 'edit' && this.value && (this.isConfigurableLine() || this.isConfigurableProduct())) {
                this.state.addLinkButton = true;
                this.state.addConfigurationButton = true;
            } else if (this.mode === 'edit' && this.value) { // TODO: see to this line
                this.state.addLinkButton = true;
                this.state.addConfigurationButton = false;
            } else {
                this.state.addLinkButton = false;
                this.state.addConfigurationButton = false;
            }
       });
    }

    isConfigurableProduct() {
        return false;
    }

    isConfigurableLine() {
        return false;
    }

    onTemplateChange(productTemplateId, dataPointId) {
        return Promise.resolve(false);
    }

    onProductChange(productId, dataPointId) {
        return Promise.resolve(false);
    }

    onLineConfigured() {}

    onEditLineConfiguration() {}

    onEditProductConfiguration() {}

    onEditConfiguration() {
        if (this.isConfigurableLine()) {
            this.onEditLineConfiguration();
        } else if (this.isConfigurableProduct()) {
            this.onEditProductConfiguration();
        }
    }

    /*
        this method should work from here
    */
    reset(record, ev) {
        if (ev && ev.target === this) {
            if (ev.data.changes && !ev.data.preventProductIdCheck && ev.data.changes.product_template_id) {
                this._onTemplateChange(record.data.product_template_id.data.id, ev.data.dataPointID);
            } else if (ev.data.changes && ev.data.changes.product_id) {
                this._onProductChange(record.data.product_id.data && record.data.product_id.data.id, ev.data.dataPointID).then(wizardOpened => {
                    if (!wizardOpened) {
                        this._onLineConfigured();
                    }
                });
            }
        }
    }
}

ProductConfiguratorField.template = "sale.ProductConfiguratorField";
registry.category("fields").add("product_configurator", ProductConfiguratorField)
