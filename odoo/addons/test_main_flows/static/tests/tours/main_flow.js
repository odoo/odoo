import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { showProductColumn } from "@account/js/tours/tour_utils";


registry.category("web_tour.tours").add('main_flow_tour', {
    steps: () => [
...stepUtils.toggleHomeMenu().map(step => {
    step.isActive = ["community", "mobile"];
    return step
}),
...stepUtils.goToAppSteps('sale.sale_menu_root', "Organize your sales activities with the Sales app."),
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Quotations')",
},
{
    isActive: ["mobile"],
    trigger: ".o_menu_toggle",
    content: "Open App menu sidebar",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_main_navbar",
},
{
// Add Stockable product
    isActive: ["desktop"],
    trigger: ".o_menu_sections .dropdown-toggle span:contains('Products')",
    content: "Let's create products.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: ".dropdown-item:contains('Products'), nav.o_burger_menu_content li[data-menu-xmlid='sale.menu_product_template_action']",
    content: "Let's create products.",
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_breadcrumb .active:contains('Products')",
},
{
    trigger: '.o-kanban-button-new',
    content: "Let's create your first product.",
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_form_sheet',
},
{
    trigger: '.o_field_widget[name=name] textarea',
    content: "Let's enter the name.",
    tooltipPosition: 'left',
    run: "edit the_flow.product",
}, {
    trigger: '.o_notebook .nav-link:contains("Inventory")',
    content: 'Go to inventory tab',
    tooltipPosition: 'top',
    run: "click",
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Manufacture")',
    content: 'Check Manufacture',
    tooltipPosition: 'right',
    run: "click",
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Buy")',
    content: 'Uncheck Buy',
    tooltipPosition: 'right',
    run: "click",
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Replenish on Order (MTO)")',
    content: 'Uncheck  Replenish on Order (MTO)',
    tooltipPosition: 'right',
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("General Information")',
    content: 'Go to main tab',
    tooltipPosition: 'top',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=taxes_id] input",
    content: "Focus on customer taxes field.",
    async run(actions) {
        await actions.click();
        const e = document.querySelector(".ui-menu-item:not(.o_m2o_dropdown_option) > a.ui-state-active");
        if (e) {
            await actions.click(e);
        } else {
            await actions.click(); // close dropdown
        }
    },
}, {
    trigger: '.o_form_button_save',
    content: "Save this product and the modifications you've made to it.",
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_form_saved",
},
stepUtils.autoExpandMoreButtons(),
{
    trigger: '.o_form_saved',
},
{
    trigger: ".oe_stat_button div[name=bom_count]",
    content: 'See Bill of material',
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_list_button_add",
    content: "Let's create a new bill of material",
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_editable",
},
{
// Add first component
    // FIXME in mobile replace list by kanban + form
    trigger: ".o_field_x2many_list_row_add > button",
    content: "Click here to add some lines.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: "Select a product, or create a new one on the fly.",
    tooltipPosition: "right",
    run: "edit the_flow.component1",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.component1')",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: "Click here to open kanban search mobile.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-dialog .btn:contains('New')",
    content: "Click here to add new line.",
    tooltipPosition: "left",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.modal-body .o_form_editable .o_field_widget[name="name"] textarea',
    content: "Select a product, or create a new one on the fly.",
    tooltipPosition: "right",
    run: "edit the_flow.component1",
}, {
// Edit first component
    isActive: ["desktop"],
    trigger: ".o_selected_row .o_external_button",
    content: "Click here to edit your component",
    tooltipPosition: "right",
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("Inventory")',
    content: 'Go to inventory tab',
    tooltipPosition: 'top',
    run: "click",
}, {
    // FIXME WOWL: can't toggle boolean by clicking on label (only with tour helpers, only in dialog ???)
    // trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Replenish on Order (MTO)")',
    trigger: '.o_field_widget[name=route_ids] .form-check:contains("Replenish on Order (MTO)") input',
    content: 'Check Replenish on Order (MTO)',
    tooltipPosition: 'right',
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("Purchase")',
    content: 'Go to purchase tab',
    tooltipPosition: 'top',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=seller_ids] .o_field_x2many_list_row_add > button",
    content: "Let's enter the cost price",
    tooltipPosition: 'right',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains(the_flow.component1)",
},
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=partner_id] input",
    content: 'Select a seller',
    tooltipPosition: 'top',
    run: "edit the_flow.vendor",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.vendor')",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=seller_ids] .o-kanban-button-new",
    content: "Let's select a vendor",
    tooltipPosition: 'bottom',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .o_form_editable div:contains('Vendor')",
},
{
    isActive: ["mobile"],
    trigger: ".o_form_editable .o_field_many2one[name=partner_id] input",
    content: "Select a vendor, or create a new one on the fly.",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .o_create_button",
    content: "Select a vendor, or create a new one on the fly.",
    tooltipPosition: "right",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=name] input:not(.o_invisible_modifier)",
    content: 'Select a seller',
    tooltipPosition: 'top',
    run: "edit the_flow.vendor",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(create vendor)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .o_form_button_save",
    content: "Save this product and the modifications you've made to it.",
    tooltipPosition: 'right',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: "body:has(.modal:contains(create vendors))",
},
{
    trigger: ".o_field_widget[name=price] input",
    content: 'Set the cost price',
    tooltipPosition: 'right',
    run: "edit 1",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=min_qty] + .o_field_widget[name=uom_id] input",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_kanban_record:contains('Units')",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .o_field_widget[name=uom_id] input:value(Units)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Save & Close):enabled",
    content: 'Save & Close',
    tooltipPosition: 'right',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(Component)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Save):enabled",
    content: 'Save',
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    isActive: ["mobile"],
    trigger: ".o_form_editable",
},
{
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=code] input',
    run: "edit Test",
    // click somewhere else to exit cell focus
}, {
    isActive: ["desktop"],
    trigger: 'th:contains("Unit")',
    run: "click",
    // click somewhere else to exit cell focus
}, {
    isActive: ["desktop"],
    trigger: '.breadcrumb .o_back_button',
    content: 'Go back',
    tooltipPosition: 'bottom',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains('the_flow.product')",
},
{
// Add second component
    isActive: ["desktop"],
    trigger: ".o_field_x2many_list_row_add > button",
    content: "Click here to add some lines.",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_form_editable",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_x2many_list_row_add > button",
    content: "Click here to add some lines.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: "Click here to open kanban search mobile.",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-dialog .btn:contains(New)",
    content: "Click here to add new line.",
    tooltipPosition: "left",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-body .o_form_editable .o_field_widget[name=name] textarea",
    content: "Select a product, or create a new one on the fly.",
    tooltipPosition: "right",
    run: "edit the_flow.component2",
},
{
    isActive: ["desktop"],
    trigger: '.o_field_widget[name=bom_line_ids] .o_data_row:nth-child(2).o_selected_row',
},
{
    isActive: ["desktop"],
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: "Select a product, or create a new one on the fly.",
    tooltipPosition: "right",
    run: "edit the_flow.component2",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.component2')",
    run: "click",
}, {
// Edit second component
    isActive: ["desktop"],
    trigger: ".o_selected_row .o_external_button",
    content: "Click here to edit your component",
    tooltipPosition: "right",
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("Purchase")',
    content: 'Go to purchase tab',
    tooltipPosition: 'top',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=seller_ids] .o-kanban-button-new",
    content: "Let's select a vendor",
    tooltipPosition: 'bottom',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .o_form_editable div:contains(Vendor)",
},
{
    isActive: ["mobile"],
    trigger:
        ".modal:not(.o_inactive_modal) .o_form_editable .o_field_many2one[name='partner_id'] input",
    content: "Select a vendor, or create a new one on the fly.",
    tooltipPosition: "bottom",
    run: "click",
},
...stepUtils.mobileKanbanSearchMany2X('Vendor', 'the_flow.vendor'),
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=seller_ids] .o_field_x2many_list_row_add > button",
    content: "Let's enter the cost price",
    tooltipPosition: 'right',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains(the_flow.component2)",
},
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=partner_id] input",
    content: 'Select a seller',
    tooltipPosition: 'top',
    run: "edit the_flow.vendor",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item:first > a:contains('the_flow.vendor')",
    run: "click",
},
{
    trigger: ".o_field_widget[name=partner_id] .o_external_button",
},
{
    trigger: ".o_field_widget[name=price] input",
    content: 'Set the cost price',
    tooltipPosition: 'right',
    run: "edit 1",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=min_qty] + .o_field_widget[name=uom_id] input",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_kanban_record:contains('Units')",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .o_field_widget[name=uom_id] input:value(Units)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Save & Close)",
    content: 'Save & Close',
    tooltipPosition: 'right',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(create component)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Save):enabled",
    content: 'Save',
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    isActive: ["mobile"],
    trigger: ".o_form_editable",
},
{
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=code] input',
    run: "edit Test",
    // click somewhere else to exit cell focus
}, {
    isActive: ["desktop"],
    trigger: 'th:contains("Unit")',
    run: "click",
    // click somewhere else to exit cell focus
}, {
    trigger: '.o_back_button',
    content: 'Go back',
    tooltipPosition: 'bottom',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains('the_flow.product')",
},
{
    isActive: ["desktop"],
    trigger: '.breadcrumb .o_back_button',
    content: 'Go back',
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_breadcrumb .active:contains('Bill of Materials')",
},
{
    trigger: '.o_back_button',
    content: 'Go back',
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_breadcrumb .active:contains('the_flow.product')",
},
{
    trigger: '.o_back_button',
    content: 'Go back',
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_kanban_view',
},
{
// Add service product
    trigger: '.o-kanban-button-new',
    content: "Let's create your second product.",
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_form_sheet',
},
{
    trigger: '.o_field_widget[name=name] textarea',
    content: "Let's enter the name.",
    tooltipPosition: 'left',
    run: "edit the_flow.service",
}, {
    trigger: '.o_field_widget[name="type"] input[data-value="service"]',
    content: 'Set to service',
    tooltipPosition: 'left',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=taxes_id] input",
    content: "Focus on customer taxes field.",
    async run(actions) {
        await actions.click();
        const e = document.querySelector(
            ".o_field_widget[name=taxes_id] .o-autocomplete--dropdown-item:not(.o_m2o_dropdown_option) > a"
        );
        if (e) {
            await actions.click(e);
        } else {
            await actions.click(); // close dropdown
        }
    },
}, {
    trigger: ".o_field_widget[name=service_policy] input",
    content: 'Change service policy',
    tooltipPosition: 'left',
    run: "click",
}, {
    content: "Select",
    trigger: ".o_select_menu_item:contains(Based on Timesheets)",
    run: "click",
},  {
    trigger: ".o_field_widget[name=service_tracking] input",
    content: 'Change service policy',
    tooltipPosition: 'left',
    run: "click",
}, {
    content: "Select",
    trigger: ".o_select_menu_item:contains(Task)",
    run: "click",
},{
    isActive: ["desktop"],
    trigger: '.o_field_widget[name=project_id] input',
    content: 'Choose project',
    tooltipPosition: 'left',
    run: "edit the_flow.project",
}, {
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=project_id] input',
    content: 'Choose project',
    tooltipPosition: 'left',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-dialog .btn:contains('New')",
    content: "Click here to add new line.",
    tooltipPosition: "left",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(Project)",
},
{
    isActive: ["mobile"],
    trigger: '.modal:not(.o_inactive_modal) .o_field_widget[name=name] textarea',
    content: "Let's enter the name.",
    tooltipPosition: 'left',
    run: "edit the_flow.project",
}, {
    isActive: ["desktop"],
    trigger: ".o-autocomplete--dropdown-item > a:contains('the_flow.project')",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Save):enabled",
    content: 'Save',
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    trigger: '.o_form_status_indicator .o_form_button_save',
    content: "Save this product and the modifications you've made to it.",
    tooltipPosition: 'bottom',
    run: "click",
},
// Create an opportunity
...stepUtils.toggleHomeMenu(),
...stepUtils.goToAppSteps('crm.crm_menu_root', "Organize your sales activities with the CRM app."),
{
    trigger: '.o_opportunity_kanban .o_kanban_renderer',
},
{
    trigger: ".o-kanban-button-new",
    content: "Click here to create your first opportunity and add it to your pipeline.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name=name] input",
    content: "Choose a name for your opportunity.",
    tooltipPosition: "right",
    run: "edit the_flow.opportunity",
}, {
    isActive: ["desktop"],
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] input",
    content: "Write the name of your customer to create one on the fly, or select an existing one.",
    tooltipPosition: "left",
    run: "edit the_flow.customer",
}, {
    isActive: ["mobile"],
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] input",
    content: "Write the name of your customer to create one on the fly, or select an existing one.",
    tooltipPosition: "left",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-dialog .btn:contains('New')",
    content: "Click here to add new line.",
    tooltipPosition: "left",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(Contact)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .o_field_widget[name=name] input:not(.o_invisible_modifier)",
    content: "Let's enter the name.",
    tooltipPosition: 'left',
    run: "edit the_flow.customer",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item:first > a:contains('the_flow.customer')",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(Contact)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Save):enabled",
    content: 'Save',
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] .o_external_button", // Wait name_create
},
{
    trigger: ".o_kanban_quick_create .o_kanban_add",
    content: "Click here to add your opportunity.",
    tooltipPosition: "right",
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_kanban_group:first .o_kanban_record span:contains('the_flow.opportunity')",
    content: "Drag & drop opportunities between columns as you progress in your sales cycle.",
    tooltipPosition: "right",
    run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(2))",
}, {
    isActive: ["desktop"],
    trigger: ".o_kanban_group:eq(2) > .o_kanban_record span:contains('the_flow.opportunity')",
    content: "Click on an opportunity to zoom to it.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_kanban_group:first .o_kanban_record span:contains('the_flow.opportunity')",
    content: "Open the_flow.opportunity",
    tooltipPosition: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_statusbar_status button:contains('New')",
    content: "Open statusbar's dropdown.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o-dropdown--menu .o-dropdown-item:contains('Proposition')",
    content: "Change status from New to proposition.",
    tooltipPosition: "bottom",
    run: "click",
},
// Create a quotation
        ...stepUtils.statusbarButtonsSteps("New Quotation", "Create a quotation"),
// Searchable label field does't support on the fly creation of products. Use the product column instead.
...showProductColumn("product_template_id"),
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=order_line] .o_field_x2many_list_row_add > button",
    content: "Click here to add some lines to your quotations.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=order_line] .btn:contains(Add)",
    content: "Click here to add some lines to your quotations.",
    tooltipPosition: "bottom",
    run: "click",
}, {
    /**
     * We need both triggers because the "sale_product_configurator" module replaces the
     * "product_id" field with a "product_template_id" field.
     * This selector will still only ever select one element.
     */
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: "Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically.",
    tooltipPosition: "right",
    run: "edit the_flow.product",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item:first > a:contains('the_flow.product')",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: `body:not(:has(.o_popover)) .o_data_row:eq(0) [name=product_template_id] input:value(the_flow.product)`,
},
{
    isActive: ["desktop"],
    trigger: "[name=tax_totals] .o_list_monetary:contains($ 1.15)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(Order Lines)",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=product_id] input",
    content: "Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically.",
    tooltipPosition: "right",
    run: "click",
},
...stepUtils.mobileKanbanSearchMany2X('Product', 'the_flow.product'),
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=order_line] button:contains(Add Line)",
    content: "Click here to add some lines to your quotations.",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(Order Lines)",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains('Save & Close')",
    content: 'Save & Close',
    tooltipPosition: 'right',
    run: "click",
}, {
    // check if the new record is displayed
    isActive: ["mobile"],
    trigger: ".o_kanban_record:contains('the_flow.product')",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=order_line] .btn:contains(Add)",
    content: "Click here to add some lines to your quotations.",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=order_line] .o_data_row:nth-child(2).o_selected_row",
},
{
    /**
     * We need both triggers because the "sale_product_configurator" module replaces the
     * "product_id" field with a "product_template_id" field.
     * This selector will still only ever select one element.
     */
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: "Select a product",
    tooltipPosition: "right",
    run: "edit the_flow.service",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item:first > a:contains('the_flow.service')",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: `body:not(:has(.o_popover)) .o_data_row:eq(1) [name=product_template_id] input:value(the_flow.service)`,
},
{
    isActive: ["desktop"],
    trigger: "[name=tax_totals] .o_list_monetary:contains($ 2.30)",
},
{
    isActive: ["desktop"],
    content: "click somewhere else to exit cell focus",
    trigger: "body",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=order_line] .o_kanban_record:contains(the_flow.product)',
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=product_id] input",
    content: "Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically.",
    tooltipPosition: "right",
    run: "click",
},
...stepUtils.mobileKanbanSearchMany2X('Product', 'the_flow.service'),
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Order Lines')",
},
{
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains('Save & Close')",
    content: 'Save & Close',
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
...stepUtils.statusbarButtonsSteps('Send', "Try to send it to email", ".o_statusbar_status .dropdown-toggle:contains('Quotation')"),
{
    isActive: ["body:not(:has(.modal-footer button[name='action_send_mail']))"],
    trigger: ".modal .modal-footer button[name='document_layout_save']",
    content: "let's continue",
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: ".o-mail-RecipientsInputTagsListPopover input",
    content: "Enter an email address",
    tooltipPosition: "right",
    run: "edit test@the_flow.com",
}, {
    trigger: ".o-mail-RecipientsInputTagsListPopover .btn-primary:contains(Set Email)",
    content: "Save your changes",
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Send)",
    content: "Try to send it to email",
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
...stepUtils.statusbarButtonsSteps('Confirm', "Confirm this quotation"),
...stepUtils.toggleHomeMenu(),
...stepUtils.goToAppSteps('stock.menu_stock_root', 'Go to Inventory'),
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Inventory Overview')",
},
{
    isActive: ["mobile"],
    trigger: ".o_menu_toggle",
    content: "Open App menu sidebar",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: '.o_main_navbar',
},
{
    isActive: ["desktop"],
    trigger: ".o_menu_sections button[data-menu-xmlid='stock.menu_stock_warehouse_mgmt']",
    content: "Go to Operations",
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: ".dropdown-item[data-menu-xmlid='stock.menu_reordering_rules_replenish'], nav.o_burger_menu_content li[data-menu-xmlid='stock.menu_reordering_rules_replenish']",
    content: "Replenishment",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: "span:contains('Replenishment')",
},
{
    isActive: ["mobile"],
    trigger: ".o_control_panel_navigation .btn .fa-search",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains('Replenishment')",
},
{
    isActive: ["desktop"],
    trigger: "td:contains('the_flow.component2')",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: "span:contains('the_flow.component2')",
    run: "click",
},
{
    trigger: ".o_field_widget[name=product_min_qty] input",
    content: "Set the minimum product quantity",
    tooltipPosition: "right",
    run: "edit 1",
}, {
    trigger: ".o_field_widget[name=product_max_qty] input",
    content: "Set the maximum product quantity",
    tooltipPosition: "right",
    run: "edit 10",
}, {
    isActive: ["desktop"],
    trigger: ".o_list_button_save",
    content: "Save this reordering rule",
    tooltipPosition: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_form_button_save",
    content: "Save this reordering rule",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_form_saved",
},
{
    isActive: ["mobile"],
    trigger: ".o_back_button",
    run: "click",
},
{
    isActive: ["mobile"],
    content: "Switch to list view to access the replenish buttons",
    trigger: ".o_cp_switch_buttons .dropdown-toggle",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".dropdown-item:has(.oi-view-list)",
    run: "click",
},
{
    isActive: ["mobile"],
    content: "Replenish the component to generate a purchase order",
    trigger: ".o_replenish_buttons",
    run: "click",
},
//Go to purchase:
...stepUtils.toggleHomeMenu(),



...stepUtils.goToAppSteps('purchase.menu_purchase_root', 'Go to Purchase'),
{
    isActive: ["desktop"],
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.vendor")) .o_data_cell:first',
    content: 'Select the generated request for quotation',
    tooltipPosition: 'bottom',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.o_kanban_record:contains("the_flow.vendor")',
    content: 'Select the generated request for quotation',
    tooltipPosition: 'bottom',
    run: "click",
},
...stepUtils.statusbarButtonsSteps('Confirm Order', "Confirm quotation", ".o_statusbar_status .dropdown-toggle:contains('RFQ')"),
...stepUtils.statusbarButtonsSteps('Receive', "Receive Product", ".o_statusbar_status .dropdown-toggle:contains('Purchase Order')"),
...stepUtils.statusbarButtonsSteps('Validate', "Validate", ".o_statusbar_status:contains('Ready')"),
...stepUtils.toggleHomeMenu(),
...stepUtils.goToAppSteps('mrp.menu_mrp_root', 'Go to Manufacturing'),
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Manufacturing Orders'), .o_breadcrumb .active:contains('Work Centers Overview')",
},
{
    isActive: ["mobile"],
    trigger: ".o_menu_toggle",
    content: "Open App menu sidebar",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_menu_sections button[data-menu-xmlid='mrp.menu_mrp_manufacturing']",
    content: 'Click on Operations menuitem',
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".dropdown-item[data-menu-xmlid='mrp.menu_mrp_production_action'], nav.o_burger_menu_content li[data-menu-xmlid='mrp.menu_mrp_production_action']",
    content: 'Open manufacturing orders',
    tooltipPosition: 'bottom',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.product")):first .o_data_cell:first',
    content: 'Select the generated manufacturing order',
    tooltipPosition: 'bottom',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Manufacturing Orders')",
},
{
    isActive: ["mobile"],
    trigger: '.o_kanban_record:contains("the_flow.product"):first',
    content: 'Select the generated manufacturing order',
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_field_widget[name=qty_producing] input",
    content: 'Set the quantity producing',
    tooltipPosition: "right",
    run: "edit 1 && click body",
},
...stepUtils.statusbarButtonsSteps('Produce All', "Produce All", ".o_statusbar_status .dropdown-toggle:contains('To Close')"),
...stepUtils.toggleHomeMenu(),
...stepUtils.goToAppSteps('sale.sale_menu_root', "Organize your sales activities with the Sales app."),
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Quotations')",
},
{
    isActive: ["mobile"],
    trigger: ".o_menu_toggle",
    content: "Open app menu.",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_menu_sections button[data-menu-xmlid='sale.sale_order_menu']",
    content: "Go to Sales menu",
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: ".dropdown-item[data-menu-xmlid='sale.menu_sale_quotations'], nav.o_burger_menu_content li[data-menu-xmlid='sale.menu_sale_quotations']",
    content: "Go to the sales orders",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: '.o_control_panel .o_breadcrumb:contains("Quotations")',
},
{
    isActive: ["desktop"],
    trigger: ".o_data_cell:contains('the_flow.customer')",
    content: "Go to the last sale order",
    tooltipPosition: "right",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: '.o_navbar_breadcrumbs .o_breadcrumb:contains("Quotations")',
},
{
    isActive: ["mobile"],
    trigger: ".o_kanban_record:contains('the_flow.customer')",
    content: "Go to the last sale order",
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: '.o_navbar_breadcrumbs .o_breadcrumb:contains("S0")',
},
{
    isActive: ["desktop"],
    trigger: '.o_breadcrumb .active:contains("S0")',
},
stepUtils.autoExpandMoreButtons(true),
{
    isActive: ["mobile"],
    trigger: '.o_navbar_breadcrumbs .o_breadcrumb:contains("S0")',
},
{
    isActive: ["desktop"],
    trigger: 'button[name="action_view_project_ids"].oe_stat_button',
    content: 'See Tasks/Projects',
    tooltipPosition: 'right',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: 'button[name="action_view_project_ids"].oe_stat_button',
    content: 'See Tasks/Projects',
    tooltipPosition: 'bottom',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: '.o_kanban_load_more > button',
    content: 'Click to load more records',
    tooltipPosition: 'bottom',
    run: 'click',
},
{
    trigger: 'article.o_kanban_record',
    content: 'Open the Kanban Record',
    run: "click",
},
{
    trigger: '.o_form_view div.o_notebook_headers',
},
{
    trigger: 'button.nav-link:contains(Timesheets)',
    content: 'Click on Timesheets page to log a timesheet',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: 'div[name="timesheet_ids"] td.o_field_x2many_list_row_add button',
    content: 'Click on Add a line to create a new timesheet into the task.',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.o-kanban-button-new',
    content: 'Open the full search field',
    tooltipPosition: 'bottom',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: 'div[name="timesheet_ids"] div[name="name"] input',
    content: 'Enter a description this timesheet',
    run: "edit 10 hours",
}, {
    isActive: ["mobile"],
    trigger: '.modal-content.o_form_view div[name="name"] input',
    content: 'Enter a description this timesheet',
    run: "edit 10 hours",
}, {
    isActive: ["desktop"],
    trigger: 'div[name="timesheet_ids"] div[name="unit_amount"] input',
    content: 'Enter one hour for this timesheet',
    run: "edit 10",
}, {
    isActive: ["mobile"],
    trigger: '.modal-content.o_form_view div[name="unit_amount"] input',
    content: 'Enter one hour for this timesheet',
    run: "edit 10",
},
{
    isActive: ["mobile"],
    content: "save",
    trigger: ".modal .o_form_button_save",
    run: "click",
},
{
    isActive: ["desktop"],
    content: "save",
    trigger: ".o_form_button_save",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('the_flow.service')",
},
{
    isActive: ["mobile"],
    trigger: ".o_back_button",
    content: 'Back to the task',
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: 'div:not(.o_form_editable)', // Waiting save
},
{
    isActive: ["desktop"],
    trigger: '.breadcrumb .breadcrumb-item .dropdown-toggle',
    content: 'Open the breadcrumb dropdown',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: '.o-overlay-container .dropdown-menu a',
    content: 'Back to the sale order',
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: "div.o_breadcrumb:contains('Tasks') .o_back_button",
    content: 'Back to the sale order',
    tooltipPosition: "bottom",
    run: "click",
},
...stepUtils.statusbarButtonsSteps('Create Invoice', "Validate", ".o_field_widget[name=order_line]"),
{
    trigger: ".modal .modal-footer .btn-primary",
    content: "Create and View Invoices",
    tooltipPosition: "bottom",
    run: "click",
},
{
    content: "Wait create and view invoices is done",
    trigger: "body:not(:has(.modal))",
},
...stepUtils.statusbarButtonsSteps('Confirm', "Validate", ".o_breadcrumb .active:contains('Draft Invoice')"),
...stepUtils.statusbarButtonsSteps('Pay', "Pay", ".o_statusbar_status .dropdown-toggle:contains('Posted')"),
{
    trigger: ".modal .modal-footer .btn-primary",
    content: "Validate",
    tooltipPosition: "bottom",
    run: "click",
},
{
    content: "Wait validate is done",
    trigger: "body:not(:has(.modal))",
},
{
    isActive: ["community"],
    content: "wait for payment registration to succeed",
    trigger: "span.text-bg-success:contains('Paid')",
},
    ...stepUtils.toggleHomeMenu(),
    stepUtils.goToAppSteps('accountant.menu_accounting', 'Go to Accounting')[2], // 2 -> Ent only
{
    isActive: ["enterprise", "desktop"],
    trigger: "div.o_account_kanban a.oe_kanban_action span:contains('Bank')",
    content: "Open the bank reconciliation widget",
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: "button.o_switch_view.o_list",
    content: "Move back to the list view",
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: "button.o_list_button_add",
    content: "Create a new bank transaction",
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: '.o_field_widget[name=amount] input',
    content: "Write the amount received.",
    tooltipPosition: "bottom",
    run: "edit 11.00",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: ".o_selected_row .o_field_widget[name=payment_ref] input",
    content: "Let's enter a name.",
    run: "edit the_flow.statement.line",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: ".o_selected_row .o_field_widget[name=partner_id] input",
    content: "Write the name of your customer.",
    tooltipPosition: "bottom",
    run: "edit the_flow.customer",
}, {
    isActive: ["desktop", "enterprise"],
    trigger: ".ui-menu-item:first > a:contains('the_flow.customer')",
    run: "click",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: ".o_selected_row .o_field_widget[name=partner_id] .o_external_button",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: '.o_list_button_save',
    content: 'Save.',
    tooltipPosition: 'bottom',
    run: "click",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: ".o_list_button_add",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: "button.o_switch_view.o_kanban",
    content: "Move back to the kanban view",
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: ".o_kanban_record span:contains('the_flow.customer')",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: ".o_kanban_record span:contains('the_flow.customer')",
    content: "Select the newly created bank transaction",
    run: "click",
},
// exit reconciliation widget
stepUtils.toggleHomeMenu()[0],
{
    isActive: ["desktop", "enterprise"],
    trigger: `.o_app[data-menu-xmlid="accountant.menu_accounting"]`,
    run: "click",
},
{
    isActive: ["desktop", "enterprise"],
    content: "check that we're back on the dashboard",
    trigger: 'a:contains("Sales")',
}]});
