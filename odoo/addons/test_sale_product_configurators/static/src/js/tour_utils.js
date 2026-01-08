/** @odoo-module **/

function addOptionalProduct(productName) {
    return {
        trigger: `table.o_sale_product_configurator_table_optional tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("${productName}")) td.o_sale_product_configurator_price button:contains("Add")`,
        content: `Add ${productName}`,
    };
}

function increaseProductQuantity(productName) {
    return {
        trigger: `table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("${productName}")) td.o_sale_product_configurator_qty div>button:has(i.fa-plus)`,
        content: `Increase quantity of ${productName}`,
    };
}

function selectAttribute(productName, attributeName, attributeValue, attributeType='radio') {
    switch (attributeType) {
        case 'color':
            return {
                trigger: `table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("${productName}")) td>div[name="ptal"]:has(div>label:contains("${attributeName}")) label[title="${attributeValue}"]`,
                content: `Select ${attributeValue} for ${productName} ${attributeName}`,
            };
        case 'multi':
        case 'pills':
        case 'radio':
            return {
                trigger: `table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("${productName}")) td>div[name="ptal"]:has(div>label:contains("${attributeName}")) span:contains("${attributeValue}")`,
                content: `Select ${attributeValue} for ${productName} ${attributeName}`,
            };
        case 'select':
            return {
                trigger: `table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("${productName}")) td>div[name="ptal"]:has(div>label:contains("${attributeName}"))`,
                content: `Select ${attributeValue} for ${productName} ${attributeName}`,
                run: () => {
                    let $selectElement = $(`table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("${productName}")) td>div[name="ptal"]:has(div>label:contains("${attributeName}")) select`)
                    let inputValue = $selectElement.children(`option:contains(${attributeValue})`).val();
                    $selectElement.val(inputValue);
                    $selectElement[0].dispatchEvent(new Event("change"));
                }
            };
        default:
            return;
    }
}

function setCustomAttribute(productName, attributeName, customValue) {
    return {
        trigger: `table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("${productName}")) td>div[name="ptal"]:has(div>label:contains("${attributeName}")) input[type="text"]`,
        content: `Set ${customValue} as a custom attribute for ${productName} ${attributeName}`,
        run: `text ${customValue}`,
    };
}

function selectAndSetCustomAttribute(productName, attributeName, attributeValue, customValue, attributeType=undefined) {
    return [
        selectAttribute(productName, attributeName, attributeValue, attributeType),
        setCustomAttribute(productName, attributeName, customValue),
    ]
}

function assertPriceTotal(total) {
    return {
        trigger: `table.o_sale_product_configurator_table tr>td[colspan=4] span:contains("${total}")`,
        content: `Assert that the total is ${total}`,
        isCheck: true,
    };
}

function assertProductNameContains(productName) {
    return {
        trigger: `table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("${productName}"))`,
        content: `Assert that the productName contains ${productName}`,
        isCheck: true,
    };
}

export default {
    addOptionalProduct,
    increaseProductQuantity,
    selectAttribute,
    setCustomAttribute,
    selectAndSetCustomAttribute,
    assertPriceTotal,
    assertProductNameContains,
};
