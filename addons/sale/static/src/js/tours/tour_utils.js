function createNewSalesOrder() {
    return [
        {
            trigger: '.o_sale_order',
        }, {
            content: "Create new order",
            trigger: '.o_list_button_add',
            run: 'click',
        },
    ]
}

function selectCustomer(customerName) {
    return [
        {
            content: `Select customer ${customerName}`,
            trigger: '.o_field_widget[name=partner_id] input',
            run: `edit ${customerName}`,
        },
        {
            trigger: `ul.ui-autocomplete > li > a:contains("${customerName}")`,
            run: 'click',
        },
    ];
}

function addProduct(productName, rowNumber=1) {
    return [
        {
            content: `Add product ${productName}`,
            trigger: 'a:contains("Add a product")',
            run: 'click',
        },
        {
            content: 'wait for new row to be created',
            trigger: `.o_data_row:nth-child(${rowNumber})`,
        },
        {
            trigger: 'div[name="product_template_id"] input',  // TODO VFE o_selected_row
            run: `edit ${productName}`,
        },
        {
            trigger: `ul.ui-autocomplete a:contains("${productName}")`,
            run: 'click',
        },
    ];
}

function clickSomewhereElse() {
    return [
        // TODO find a way for onchange to finish first ?
        {
            content: 'click somewhere else to exit cell focus',
            trigger: 'a[name=order_lines]',  // click on notebook tab to stop the sol edit mode.
            run: 'click',
        },
        {
            content: 'check that the soline is not focused anymore',
            trigger: 'table.o_section_and_note_list_view:not(:has(.o_selected_row))',
        }
    ]
}

function checkSOLDescriptionContains(productName, text) {
    // TODO in the future: look directly into the textarea value
    let trigger = '.o_field_product_label_section_and_note_cell';
    if (productName) {
        trigger = `${trigger}:has(:contains("${productName}"), input:value("${productName}"))`;
    }
    if (text) {
        trigger = `${trigger} .o_input`;
    }
    return { trigger };
}

function editLineMatching(productName, text) {
    let base_step = checkSOLDescriptionContains(productName, text);
    base_step['run'] = 'click';
    return base_step;
}

function editConfiguration() {
    return {
        trigger: '[name=product_template_id] button.fa-pencil',
        run: 'click',
    }
}

export default {
    createNewSalesOrder,
    selectCustomer,
    addProduct,
    checkSOLDescriptionContains,
    editLineMatching,
    editConfiguration,
    clickSomewhereElse,
};
