// TODO try and migrate to stock / tour helpers but issue with backend_assets vs backend_test import
const { DateTime } = luxon;

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
                DateTime.now = () => DateTime.fromFormat(jsDate, fmt);
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
            tooltipPosition: "bottom",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit(vendorName, input || this.anchor);
            },
        },
        {
            content: "Select vendor from many to onw",
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
            tooltipPosition: "bottom",
            async run(actions) {
                const input = this.anchor.querySelector("input");
                await actions.edit(warehouseName, input || this.anchor);
            },
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
 * @param {number} wait Numebr of milliseconds before going to next step (eg. 1000).
 * *I could find a workaround for the Timeout, because nothing on UI changes, just need to wait server round trip.
 */
export function setSuggestParameters({
    basedOn = false,
    nbDays = false,
    factor = false,
    wait = false,
}) {
    const steps = [];
    if (basedOn) {
        steps.push({
            trigger: ".o_TimePeriodSelectionField",
            async run(actions) {
                await actions.click(this.anchor.querySelector(".o_select_menu_toggler"));
                await new Promise((r) => setTimeout(r, 300));
                await actions.click(`.o_popover .o_select_menu_item:contains('${basedOn}')`);
            },
        });
    }
    if (nbDays) {
        steps.push({
            trigger: "input.o_PurchaseSuggestInput:eq(0)",
            run: `edit ${nbDays}`,
        });
    }
    if (factor) {
        steps.push({
            trigger: "input.o_PurchaseSuggestInput:eq(1)",
            run: `edit ${factor}`,
        });
    }
    if (wait) {
        steps.push({
            trigger: ".o_TimePeriodSelectionField",
            async run() {
                await new Promise((r) => setTimeout(r, wait));
            },
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
 * Toggles the Suggest feature ON/OFF
 */
export function toggleSuggest() {
    return {
        trigger: 'button[name="toggle_suggest_catalog"]',
        run: "click",
    };
}
