/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useEffect } from '@odoo/owl';
import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export class SaleOrderLineProductField extends Many2OneField {
    static props = {
        ...Many2OneField.props,
        readonlyField: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        let isMounted = false;
        let isInternalUpdate = false;
        const { updateRecord } = this;
        this.updateRecord = (value) => {
            isInternalUpdate = true;
            return updateRecord.call(this, value);
        };
        useEffect(value => {   
            if (!isMounted) {
                isMounted = true;
            } else if (value && isInternalUpdate) {
                // we don't want to trigger product update when update comes from an external sources,
                // such as an onchange, or the product configuration dialog itself
                if (this.relation === "product.template") {
                    this._onProductTemplateUpdate();
                } else {
                    this._onProductUpdate();
                }
            }
            isInternalUpdate = false;
        }, () => [Array.isArray(this.value) && this.value[0]]);
    }

    get isProductClickable() {
        // product form should be accessible if the widget field is readonly
        // or if the line cannot be edited (e.g. locked SO)
        return (
            this.props.readonlyField ||
            (this.props.record.model.root.activeFields.order_line &&
                this.props.record.model.root._isReadonly("order_line"))
        );
    }
    get hasExternalButton() {
        // Keep external button, even if field is specified as 'no_open' so that the user is not
        // redirected to the product when clicking on the field content
        const res = super.hasExternalButton;
        return res || (!!this.props.record.data[this.props.name] && !this.state.isFloating);
    }
    get hasConfigurationButton() {
        return this.isConfigurableLine || this.isConfigurableTemplate;
    }
    get isConfigurableLine() {
        return false;
    }
    get isConfigurableTemplate() {
        return false;
    }

    get configurationButtonHelp() {
        return _t("Edit Configuration");
    }

    get configurationButtonIcon() {
        return "btn btn-secondary fa " + this.configurationButtonFAIcon();
    }

    configurationButtonFAIcon() {
        return "fa-pencil";
    }

    onClick(ev) {
        // Override to get internal link to products in SOL that cannot be edited
        if (this.props.readonly) {
            ev.stopPropagation();
            this.openAction();
        } else {
            super.onClick(ev);
        }
    }

    async _onProductTemplateUpdate() {}
    async _onProductUpdate() {} // event_booth_sale, event_sale, sale_renting

    onEditConfiguration() {
        if (this.isConfigurableLine) {
            this._editLineConfiguration();
        } else {
            this._editProductConfiguration();
        }
    }
    _editLineConfiguration() {} // event_booth_sale, event_sale, sale_renting
    _editProductConfiguration() {} // sale_product_configurator, sale_product_matrix
}

SaleOrderLineProductField.template = "sale.SaleProductField";

export const saleOrderLineProductField = {
    ...many2OneField,
    component: SaleOrderLineProductField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneField.extractProps(...arguments);
        props.readonlyField = dynamicInfo.readonly;
        return props;
    },
};

registry.category("fields").add("sol_product_many2one", saleOrderLineProductField);
