import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_basic_stock_flow_with_minimal_access_rights", {
    steps: () => [
        {
            trigger: ".o_menuitem[href='/odoo/inventory']",
            run: "click",
        },
        {
            trigger: "button[data-menu-xmlid='stock.menu_stock_warehouse_mgmt']",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item[data-menu-xmlid='stock.in_picking']",
            run: "click",
        },
        {
            content: "check that at least one picking is present in the view",
            trigger: ".o_stock_list_view_view .o_data_row",
        },
        {
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            trigger: ".o_input[id=partner_id_0]",
            run: "edit Test Partner",
        },
        {
            trigger: ".dropdown-item:contains('Test Partner')",
            run: "click",
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            run: "click",
        },
        {
            trigger: ".o_data_row .o_input",
            run: "edit Test Product",
        },
        {
            trigger: ".dropdown-item:contains('Test Product')",
            run: "click",
        },
        {
            trigger: ".o_data_cell[name=product_uom_qty]",
            run: "click",
        },
        {
            trigger: ".o_data_cell[name=product_uom_qty] .o_input",
            run: "edit 1",
        },
        {
            trigger: "button[name=action_confirm]",
            run: "click",
        },
        {
            trigger: "button[name=button_validate]",
            run: "click",
        },
        {
            trigger: ".o_arrow_button_current:contains(Done)",
        },
        {
            trigger: "button[data-menu-xmlid='stock.menu_stock_warehouse_mgmt']",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item[data-menu-xmlid='stock.out_picking']",
            run: "click",
        },
        {
            content: "check that at least one picking is present in the view",
            trigger: ".o_stock_list_view_view .o_data_row",
        },
        {
            trigger: "button:contains(New)",
            run: "click",
        },
        {
            trigger: ".o_input[id=partner_id_0]",
            run: "edit Test Partner",
        },
        {
            trigger: ".dropdown-item:contains('Test Partner')",
            run: "click",
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            run: "click",
        },
        {
            trigger: ".o_data_row .o_input",
            run: "edit Test Product",
        },
        {
            trigger: ".dropdown-item:contains('Test Product')",
            run: "click",
        },
        {
            trigger: ".o_data_cell[name=product_uom_qty]",
            run: "click",
        },
        {
            trigger: ".o_data_cell[name=product_uom_qty] .o_input",
            run: "edit 1",
        },
        {
            trigger: "button[name=action_confirm]",
            run: "click",
        },
        {
            trigger: "button[name=button_validate]",
            run: "click",
        },
        {
            trigger: ".o_arrow_button_current:contains(Done)",
        },
    ],
});
