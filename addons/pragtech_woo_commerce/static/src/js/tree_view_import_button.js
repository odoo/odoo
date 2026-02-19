/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export class WooListImportController extends ListController {
    setup() {
        super.setup();
    }

    /*
        for importing the products
        this will open the wizard for importing products
    */
    async onClickWooProductImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_woo_import_product_instance", {});
    }

        /*
        for importing the Tax
        this will open the wizard for importing Tax
    */
    async onClickWooTaxImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_import_tax", {});
    }

    /*
        for importing the products quantity
        this will open the wizard for importing products quantity
    */
    async onClickWooUpdateQuantity() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_woo_import_inventory", {});
    }

    /*
        for importing the products category
        this will open the wizard for importing products category
    */
    async onClickWooProductCategoryImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_woo_import_product_category", {});
    }

    /*
        for importing the products attributes
        this will open the wizard for importing products attributes
    */
    async onClickWooProductAttributeImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_woo_import_product_attribute", {});
    }

    /*
        for importing the products attribute values
        this will open the wizard for importing products attribute values
    */
    async onClickWooProductAttributeValueImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_woo_import_product_attribute_value", {});
    }

    /*
        for importing the products tag
        this will open the wizard for importing products tag woo
    */
    async onClickWooProductTagWooImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_import_product_tag", {});
    }

    /*
        for importing the sale order
        this will open the wizard for importing sale order
    */
    async onClickWooSaleOrderImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_import_sale_order", {});
    }

    /*
        for importing the sale order refund
        this will open the wizard for importing sale order refund
    */
    async onClickWooRefundImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_woo_import_refund_instance", {});
    }

    /*
        for importing the customers
        this will open the wizard for importing customers
    */
    async onClickWooCustomerImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_import_customer", {});
    }

    /*
        for importing the coupons
        this will open the wizard for importing coupons
    */
    async onClickWooCouponImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_woo_import_coupon_instance", {});
    }

    /*
        for importing the shipping method
        this will open the wizard for importing shipping method
    */
    async onClickWooShippingMethodImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_woo_import_shipping_method_instance", {});
    }

    /*
        for importing the payment method
        this will open the wizard for importing payment method
    */
    async onClickWooPaymentMethodImport() {
        return this.actionService.doAction("pragtech_woo_commerce.action_wizard_woo_import_payment_gateway_instance", {});
    }
}


export const WooCommerceImportListView = {
    ...listView,
    Controller: WooListImportController,
    buttonTemplate: 'WooCommerceImportList.Buttons',
};

registry.category("views").add('woo_import_product_button', WooCommerceImportListView);
registry.category("views").add('woo_import_product_category_button', WooCommerceImportListView);
registry.category("views").add('woo_import_product_attribute_button', WooCommerceImportListView);
registry.category("views").add('woo_import_product_attribute_value_button', WooCommerceImportListView);
registry.category("views").add('woo_import_product_tag_woo_button', WooCommerceImportListView);
registry.category("views").add('woo_import_sale_order_button', WooCommerceImportListView);
registry.category("views").add('woo_import_customer_button', WooCommerceImportListView);
registry.category("views").add('woo_import_coupon_button', WooCommerceImportListView);
registry.category("views").add('woo_import_shipping_method_button', WooCommerceImportListView);
registry.category("views").add('woo_import_payment_method_button', WooCommerceImportListView);
registry.category("views").add('woo_import_credit_note_button', WooCommerceImportListView);
registry.category("views").add('woo_import_tax_button', WooCommerceImportListView);

