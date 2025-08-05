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
