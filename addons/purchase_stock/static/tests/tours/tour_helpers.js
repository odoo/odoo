/**
 * Sets the date on the client to a specific timestamp using luxon's DateTime.fromFormat(jsDate, fmt)
 * @param {string} jsDate A date time string
 * @param {string} fmt The format of jsDate param (default: yyyy-LL-dd HH:mm:ss).
 */
export function freezeDateTime(jsDate, fmt = "yyyy-LL-dd HH:mm:ss") {
    return [
        {
            trigger: "body",
            run: () => {
                // Resolve luxon at runtime only, to prevent import error
                luxon.DateTime.now = () => luxon.DateTime.fromFormat(jsDate, fmt);
            },
        },
    ];
}

/**
 * Sets the vendor on a purchase order (must already on PO).
 * @param {string} vendorName An existing partner.
 */
export function selectPOVendor(vendorName) {
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
}

/**
 * Sets the WH on a purchase order (must already on PO).
 * @param {string} warehouseName An existing warehouse.
 */
export function selectPOWarehouse(warehouseName) {
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
}

/**
 * Sets the Suggest UI parameters
 * @param {string} basedOn The label value of the "Replenish based on" select options (eg. "Last 3 months")
 * @param {number} nbDays The value of the "Replenish for" input (eg. 90)
 * @param {number} factor The value of the "x ...%" input (eg. 50)
 */
export function setSuggestParameters({ basedOn = false, nbDays = false, factor = false }) {
    const steps = [];
    if (basedOn) {
        steps.push(
            {
                trigger: ".o_TimePeriodSelectionField .o_select_menu .dropdown-toggle:visible",
                run: "click",
            },
            {
                trigger: ".o_select_menu_menu:visible",
            },
            {
                trigger: `.o_select_menu_menu .o_select_menu_item:contains('${basedOn}'):visible`,
                run: "click",
            }
        );
    }
    if (nbDays !== false) {
        steps.push({
            trigger: "input.o_PurchaseSuggestInput:eq(0)",
            run: `edit ${nbDays}`,
        });
    }
    if (factor !== false) {
        steps.push({
            trigger: "input.o_PurchaseSuggestInput:eq(1)",
            run: `edit ${factor}`,
        });
    }
    return steps;
}

/**
 * Clicks on the "Catalog" button below the purchase order lines
 */
export function goToCatalogFromPO() {
    return [
        {
            content: "Go to product catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: "click",
        },
        { trigger: ".o_kanban_view.o_purchase_product_kanban_catalog_view" },
    ];
}

/**
 * Clicks on the "Back to Order" button from the Catalog view
 */
export function goToPOFromCatalog() {
    return [
        {
            content: "Go back to the PO",
            trigger: "button.o-kanban-button-back",
            run: "click",
        },
        { trigger: ".o_form_view.o_purchase_order" },
    ];
}

/**
 * @param {boolean} turnOn True to turn Suggest ON, false to turn it OFF
 */
export function toggleSuggest(turnOn) {
    return [
        {
            trigger: 'button[name="toggle_suggest_catalog"]',
            run: "click",
        },
        { trigger: `button[name="toggle_suggest_catalog"].fa-toggle-${turnOn ? "on" : "off"}` },
    ];
}
