export const purchaseForm = {
    checkLineValues(index, values) {
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

    displayOptionalField(fieldName) {
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

    /**
     * Clicks on the "Catalog" button below the purchase order lines.
     */
    openCatalog() {
        return [
            {
                content: "Go to product catalog",
                trigger: ".o_field_x2many_list_row_add > button[name='action_add_from_catalog']",
                run: "click",
            },
        ];
    },

    /**
     * Sets the vendor on a purchase order (must already on PO).
     * @param {string} vendorName An existing partner.
     */
    selectVendor(vendorName) {
        return [
            {
                content: "Fill Vendor Field on PO",
                trigger: ".o_field_res_partner_many2one[name='partner_id'] input",
                run: `edit ${vendorName}`,
            },
            {
                content: "Select vendor from many to one",
                isActive: ["auto"],
                trigger: `.ui-menu-item > a:contains(${vendorName})`,
                run: "click",
            },
        ];
    },

    /**
     * Sets the WH on a purchase order (must already on PO).
     * @param {string} warehouseName An existing warehouse.
     */
    selectWarehouse(warehouseName) {
        return [
            {
                content: "Fill Warehouse Field on PO",
                trigger: ".o_field_many2one[name='picking_type_id'] input",
                run: `edit ${warehouseName}`,
            },
            {
                content: "Select BaseWarehouse as PO WH",
                isActive: ["auto"],
                trigger: `.ui-menu-item > a:contains(${warehouseName})`,
                run: "click",
            },
        ];
    },

    createNewPO() {
        const content = "Create a New PO";
        const trigger = ".o_list_button_add, .o_form_button_create";
        return [{ content, trigger, run: "click" }];
    },
};

export const productCatalog = {
    addProduct(productName) {
        const trigger = `.o_kanban_record:contains("${productName}") button:has(.fa-plus,.fa-shopping-cart)`;
        return [{ trigger, run: "click" }];
    },

    /** Remove a product from the PO by clicking the "trash" button */
    removeProduct(productName) {
        const trigger = `.o_kanban_record:contains("${productName}") button:has(.fa-trash)`;
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

    selectSearchPanelCategory(categoryName) {
        const content = `Select the category ${categoryName}`;
        const trigger = `.o_search_panel_label_title:contains("${categoryName}")`;
        return [{ content, trigger, run: "click" }];
    },

    /**
     * Clicks on the "Back to Order" button from the Catalog view
     */
    goBackToOrder() {
        const content = "Go back to the Order";
        const trigger = "button.o-kanban-button-back";
        return [{ content, trigger, run: "click" }];
    },
};
