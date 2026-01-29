import { inputFiles } from "@web/../tests/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_basic_purchase_flow_with_minimal_access_rights", {
    steps: () => [
        {
            trigger: ".o_menuitem[href='/odoo/purchase']",
            run: "click",
        },
        {
            content: "Check that at least one RFQ is present in the view",
            trigger: ".o_purchase_dashboard_list_view .o_data_row",
        },
        {
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            trigger: ".o_input[id=partner_id_0]",
            run: "edit partner_a",
        },
        {
            trigger: ".dropdown-item:contains(partner_a)",
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
            trigger: ".o_data_cell[name=price_unit]",
            run: "click",
        },
        {
            trigger: ".o_data_cell[name=price_unit] .o_input",
            run: "edit 3",
        },
        {
            trigger: "button[name=button_confirm]",
            run: "click",
        },
        {
            trigger: ".o_statusbar_status .o_arrow_button_current:contains(Purchase Order)",
        },
        {
            content: "Upload the vendor bill",
            trigger: ".o_widget_purchase_file_uploader",
            run: async () => {
                const testFile = new File(["Vendor, Bill"], "my_vendor_bill.png", {
                    type: "image/*",
                });
                await inputFiles(".o_widget_purchase_file_uploader input", [testFile]);
            },
        },
        {
            content: "Check that we are in the invoice form view",
            trigger: ".o_statusbar_status:contains(Posted) .o_arrow_button_current:contains(Draft)",
        },
        {
            content: "Check that the invoice is linked to the sale order",
            trigger: "button[name=action_view_source_purchase_orders]",
        },
    ],
});
