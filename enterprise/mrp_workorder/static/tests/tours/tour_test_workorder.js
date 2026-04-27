/** @odoo-module **/

import { registry } from "@web/core/registry";
import helper from '@mrp_workorder/../tests/tours/tour_helper_mrp_workorder';

registry.category("web_tour.tours").add('test_serial_tracked_and_register', { steps: () => [
    {
        trigger: '.o_tablet_client_action',
        run: function() {
            helper.assert(document.querySelector('input[id="finished_lot_id_0"]').value, 'Magic Potion_1');
        }
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        // sn should have been updated to match move_line sn
        trigger: 'div.o_field_widget[name="lot_id"] input ',
        run: function() {
            helper.assert(document.querySelector('input[id="lot_id_0"]').value, 'Magic_2');
        }
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        trigger: `.btn[name="button_start"]`,
        run: "click",
    },
    {
        trigger: 'div.o_field_widget[name="lot_id"] input ',
        tooltipPosition: 'bottom',
        run: "edit Magic_3",
    },
    {
        trigger: `.ui-menu-item > a:contains("Magic_3")`,
        run: "click",
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        trigger: 'div.o_field_widget[name="finished_lot_id"] input ',
        tooltipPosition: 'bottom',
        run: "edit Magic Potion_2",
    },
    {
        trigger: `.ui-menu-item > a:contains("Magic Potion_2")`,
        run: "click",
    },
    {
        // comp sn shouldn't change when produced sn is changed
        trigger: 'div.o_field_widget[name="lot_id"] input',
        run: function() {
            helper.assert(document.querySelector('input[id="lot_id_0"]').value, 'Magic_3');
        }
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        trigger: 'div.o_field_widget[name="lot_id"] input ',
        tooltipPosition: 'bottom',
        run: "edit Magic_1",
    },
    {
        trigger: `.ui-menu-item > a:contains("Magic_1")`,
        run: "click",
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        // produced sn shouldn't change when comp sn is changed
        trigger: 'div.o_field_widget[name="finished_lot_id"] input ',
        run: function() {
            helper.assert(document.querySelector('input[id="finished_lot_id_0"]').value, 'Magic Potion_2');
        }
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        trigger: ".btn-primary[name='action_next']",
        run: "click",
    },
    {
        trigger: "button[name=do_finish]",
        run: "click",
    },
    {
        trigger: ".o_searchview_input",
        run: "click",
    },
]});

registry.category("web_tour.tours").add('test_access_shop_floor_with_multicomany', {
    url: '/odoo/action-menu',
    steps: () => [{
        content: 'Select Shop Floor app',
        trigger: 'a.o_app:contains("Shop Floor")',
        run: "click",
    },{
        content: 'Close the select workcenter panel',
        trigger: 'button.btn-close',
        run: "click",
    },{
        content: 'Check that we entered the app with first company',
        trigger: 'div.o_mrp_display',
        run: "click",
    },{
        content: 'Go back to home menu',
        trigger: '.o_home_menu',
        run: "click",
    },{
        content: 'Click on switch  company menu',
        trigger: '.o_switch_company_menu button',
        run: "click",
    },{
        content: 'Select another company',
        trigger: 'div[role="button"]:contains("Test Company")',
        run: "click",
    },{
        content: 'Check that we switched companies',
        trigger: '.o_switch_company_menu button span:contains("Test Company")',
    },{
        content: 'Select Shop Floor app',
        trigger: 'a.o_app:contains("Shop Floor")',
        run: "click",
    },{
        content: 'Close the select workcenter panel again',
        trigger: '.btn-close',
        run: "click",
    },{
        content: 'Check that we entered the app with second company',
        trigger: 'div.o_mrp_display',
        run: "click",
    },{
        content: 'Check that the WO is not clickable',
        trigger: 'div.o_mrp_display_record.o_disabled',
    }]
})

registry.category("web_tour.tours").add("test_add_component_from_shop_foor", {
    steps: () => [
        {
            trigger: ".form-check-input[name='All MO']",
            run: "click",
        },
        {
            trigger: ".form-check-input[name='Nuclear Workcenter']",
            run: "click",
        },
        {
            trigger: "button:contains('Confirm')",
            run: "click",
        },
        {
            content: "Check that we are in the MO view",
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) button:contains('Nuclear Workcenter')",
        },
        {
            content: "Add Wood to the MO components",
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) .card-footer button.fa-gear",
            run: "click",
        },
        {
            trigger: ".o_mrp_menu_dialog button:contains('Add Component')",
            run: "click",
        },
        {
            trigger: ".modal-content .o_kanban_record:has(span:contains('Super Wood'))",
            run: "click",
        },
        {
            content: "Await for the Component to be added",
            trigger: ".modal-content input.o_input[type='number']",
            run: function () {
                helper.assert(
                    document.querySelector(".modal-content input.o_input[type='number']").value,
                    "1"
                );
            },
        },
        {
            trigger: ".modal-content button.btn-close",
            run: "click",
        },
        {
            content: "Check that the Wood is visible on the MO",
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) .o_mrp_record_line:contains('Super Wood')",
        },
        {
            content: "Swap to the WO view of the Nuclear Workcenter",
            trigger: "button.btn-light:contains('Nuclear Workcenter')",
            run: "click",
        },
        {
            content: "Check that the Wood is visible on the MO",
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) .o_mrp_record_line:contains('Super Wood')",
        },
        {
            content: "Swap to the WO view of the Nuclear Workcenter",
            trigger: "button.btn-light:contains('Nuclear Workcenter')",
            run: "click",
        },
        {
            content: "Check that we are in the WO view",
            trigger: ".o_mrp_display_records .card-header .card-title:contains('Super Operation')",
        },
        {
            content: "Add Courage to the WO components",
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) .card-footer button.fa-gear",
            run: "click",
        },
        {
            trigger: ".o_mrp_menu_dialog",
        },
        {
            trigger: "button:contains('Add Component')",
            run: "click",
        },
        {
            trigger: ".modal-content .o_kanban_record:has(span:contains('Courage'))",
            run: "click",
        },
        {
            content: "Await for the Component to be added",
            trigger: ".modal-content input.o_input[type='number']",
            run: function () {
                helper.assert(
                    document.querySelector(".modal-content input.o_input[type='number']").value,
                    "1"
                );
            },
        },
        {
            trigger: ".modal-content button.btn-close",
            run: "click",
        },
        {
            content: "Check that the Courage is visible on the WO",
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) .o_mrp_record_line span:contains('Courage')",
        },
        {
            content: "Go back to the MO",
            trigger: "button.btn:contains('All MO')",
            run: "click",
        },
        {
            content: "Check that we are in the MO view",
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) button:contains('Nuclear Workcenter')",
        },
        {
            content: "Check that the Courage is visible on the MO",
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) .o_mrp_record_line span:contains('Courage')",
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("test_add_component_from_shop_foor_in_multi_step_manufacturing", {
        steps: () => [
            {
                trigger: ".form-check-input[name='Nuclear Workcenter']",
                run: "click",
            },
            {
                trigger: "button:contains('Confirm')",
                run: "click",
            },
            {
                content: "Check that we are in the MO view",
                trigger:
                    ".o_mrp_display_records:has(.card-header:contains(Lovely MO)) button:contains(Nuclear Workcenter)",
            },
            {
                content: "Add Courage to the MO components",
                trigger:
                    ".o_mrp_display_record:has(.card-header:contains(Lovely MO)) .card-footer button.btn-light.py-3",
                run: "click",
            },
            {
                trigger: ".o_mrp_menu_dialog",
            },
            {
                trigger: "button:contains(Add Component)",
                run: "click",
            },
            {
                trigger: ".modal-content .o_kanban_record:has(span:contains('Courage'))",
                run: "click",
            },
            {
                content: "Await for the Component to be added",
                trigger: ".modal-content input.o_input[type='number']",
                run: function () {
                    helper.assert(
                        document.querySelector(".modal-content input.o_input[type='number']").value,
                        "1"
                    );
                },
            },
            {
                trigger: ".modal-content button.btn-close",
                run: "click",
            },
            {
                content: "Check that the Courage is visible on the MO",
                trigger:
                    ".o_mrp_display_record:has(.card-header:contains(Lovely MO))  .o_mrp_record_line:contains(Courage)",
            },
            {
                content: "Add Courage to the MO components",
                trigger:
                    ".o_mrp_display_record:contains(Stone Tools) .card-footer button.btn-light.py-3",
                run: "click",
            },
            {
                trigger: "button:contains(Add Component)",
                run: "click",
            },
            {
                trigger: ".modal-content .o_kanban_record:has(span:contains('Courage'))",
                run: "click",
            },
            {
                content: "Await for the Component to be added",
                trigger: ".modal-content input.o_input[type='number']:value(2)",
                run() {},
            },
            {
                trigger: ".modal-content button.btn-close",
                run: "click",
            },
            {
                content: "Check that the last piece of Courage was added to the MO",
                trigger: ".o_mrp_record_line:contains(Courage) button:contains(2)",
                run: () => {},
            },
        ],
    });
