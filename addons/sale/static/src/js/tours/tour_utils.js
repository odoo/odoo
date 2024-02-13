/** @odoo-module **/

function selectCustomer(customerName) {
    return [
        {
            content: `Select customer ${customerName}`,
            trigger: '.o_field_widget[name=partner_id] input',
            run: `edit ${customerName}`,
        },
        {
            trigger: `ul.ui-autocomplete a:contains("${customerName}")`,
            run: 'click',
        },
    ];
}

function addProduct(productName) {
    return [
        {
            content: `Add product ${productName}`,
            trigger: 'a:contains("Add a product")',
            run: 'click',
        },
        {
            trigger: 'div[name="product_template_id"] input',
            run: `edit ${productName}`,
        },
        {
            trigger: `ul.ui-autocomplete a:contains("${productName}")`,
            run: 'click',
        },
    ];
}

function saveForm() {
    return [
        {
            content: "Save the form",
            trigger: '.o_form_button_save',
            run: 'click',
        },
        {
            content: "Wait for the save to complete",
            trigger: '.o_form_saved',
        },
    ];
}

export default {
    selectCustomer,
    addProduct,
    saveForm,
};
