export const stepUtils = {
    // Form view utils.
    checkPurchaseOrderLineValues(index, values) {
        const fieldAndLabelDict = {
            product: { fieldName: "product_id", label: "product" },
            quantity: { fieldName: "product_qty", label: "quantity" },
            unit: { fieldName: "product_uom_id", label: "unit of measure" },
            unitPrice: { fieldName: "price_unit", label: "unit price" },
            discount: { fieldName: "discount", label: "discount" },
            totalPrice: { fieldName: "price_subtotal", label: "subtotal price" },
        };
        const trigger = `.o_form_renderer .o_list_view.o_field_x2many tbody tr.o_data_row:eq(${index})`;
        const run = function ({ anchor }) {
            const getFieldValue = (fieldName) => {
                let selector = `td[name="${fieldName}"]`;
                if (fieldName === "product_id") {
                    // Special case for the product field because it can be replace by another field
                    selector += ",td[name='product_template_id']";
                }
                const fieldEl = anchor.querySelector(selector);
                return fieldEl ? fieldEl.innerText.replace(/\s/g, " ") : false;
            };
            for (const key in values) {
                if (!Object.keys(fieldAndLabelDict).includes(key)) {
                    throw new Error(
                        `'checkPurchaseOrderLineValues' is called with unsupported key: ${key}`
                    );
                }
                const value = values[key];
                const { fieldName, label } = fieldAndLabelDict[key];
                const lineValue = getFieldValue(fieldName);
                if (!lineValue) {
                    throw new Error(
                        `Purchase order line at index ${index} expected ${value} as ${label} but got nothing`
                    );
                } else if (lineValue !== value) {
                    throw new Error(
                        `Purchase order line at index ${index} expected ${value} as ${label} but got ${lineValue} instead`
                    );
                }
            }
        };
        return [{ trigger, run }];
    },
    displayFormOptionalField(fieldName) {
        return [
            {
                trigger:
                    ".o_form_renderer .o_list_view.o_field_x2many .o_optional_columns_dropdown button",
                run: "click",
            },
            { trigger: `input[name="${fieldName}"]:not(:checked)`, run: "click" },
            { trigger: `th[data-name="${fieldName}"]` },
        ];
    },
    openCatalog() {
        const trigger = ".o_field_x2many_list_row_add > button[name='action_add_from_catalog']";
        return [{ trigger, run: "click" }];
    },
    // Product catalog utils.
    addProduct(productName) {
        const trigger = `.o_kanban_record:contains("${productName}") button:has(.fa-plus,.fa-shopping-cart)`;
        return [{ trigger, run: "click" }];
    },
    checkProductPrice(productName, price) {
        const trigger = `.o_kanban_record:contains("${productName}") .o_product_catalog_price:contains("${price}")`;
        const content = `Check that the kanban record card for product "${productName}" has a price of ${price}`;
        return [{ content, trigger }];
    },
    checkProductUoM(productName, uom) {
        const trigger = `.o_kanban_record:contains("${productName}") .o_product_catalog_quantity:contains("${uom}")`;
        const content = `Check that the kanban record card for product "${productName}" uses ${uom} as the UoM`;
        return [{ content, trigger }];
    },
    waitForQuantity(productName, quantity) {
        const trigger = `.o_kanban_record:contains("${productName}") input[type=number]:value("${quantity}")`;
        return [{ trigger }];
    },
};
