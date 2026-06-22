export function createNewSalesOrder() {
    return [
        {
            trigger: ".o_list_view",
        },
        {
            content: "Create new order",
            trigger: '.o_list_button_add',
            run: async function ({ anchor, queryFirst }) {
                // sale_management adds dropdown to the button if there are accessible templates
                // we need this util to work out of the box without needing to care about templates
                if (anchor.classList.contains("dropdown")) {
                    anchor.click();
                    await new Promise((resolve) =>
                        requestAnimationFrame(() => setTimeout(resolve))
                    );
                    const newQuotationButton = queryFirst(
                        "div.o_popover:has(.o_sale_management_template) > button.o-dropdown-item:not(.o_sale_management_template)"
                    );
                    newQuotationButton?.click();
                } else {
                    anchor.click();
                }
            },
        },
    ];
}

export function selectCustomer(customerName) {
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

export function selectPricelist(pricelistName) {
    return [
        {
            content: `Select pricelist ${pricelistName}`,
            trigger: '.o_field_widget[name=pricelist_id] input',
            run: `edit ${pricelistName}`,
        },
        {
            trigger: `ul.ui-autocomplete > li > a:contains("${pricelistName}")`,
            run: 'click',
        },
    ];
}

export function addProduct(productName, rowNumber=1) {
    return [
        {
            content: `Add product ${productName}`,
            trigger: 'button:contains("Add Line")',
            run: 'click',
        },
        {
            content: 'wait for new row to be created',
            trigger: `.o_data_row:nth-child(${rowNumber})`,
        },
        {
            trigger: '.o_selected_row textarea.o_input',
            run: `edit ${productName}`,
        },
        {
            trigger: `ul.ui-autocomplete a:contains("${productName}")`,
            run: 'click',
        },
    ];
}

export function clickSomewhereElse() {
    return [
        // TODO find a way for onchange to finish first ?
        {
            content: 'click somewhere else to exit cell focus',
            trigger: 'button[name=order_lines]',  // click on notebook tab to stop the sol edit mode.
            run: 'click',
        },
        {
            content: 'check that the soline is not focused anymore',
            trigger: 'table.o_section_and_note_list_view:not(:has(.o_selected_row))',
        }
    ]
}

export function checkSOLDescriptionContains(productName, text) {
    // TODO in the future: look directly into the textarea value
    let trigger = '.o_field_sol_label_text';
    if (productName) {
        trigger += `:contains("${productName}")`;
    }
    if (text) {
        // for checking multiline comments
        for (const line of text.split("\n")) {
            trigger += `:contains("${line}")`;
        }
    }
    return { trigger };
}

export function editLineMatching(productName, text) {
    const base_step = checkSOLDescriptionContains(productName, text);
    base_step['run'] = 'click';
    return base_step;
}

export function editConfiguration(lineName) {
    return {
        trigger: `div[name="account_label_text_readonly"]:contains(${lineName})`,
        run: "hover && click button.fa-pencil",
    };
}
