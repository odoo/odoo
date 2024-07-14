/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const oldWriteText = navigator.clipboard.writeText;

registry.category("web_tour.tours").add('appointment_crm_meeting_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
        run: 'click',
    }, {
        trigger: '.o_kanban_record:contains("Test Opportunity")',
        extra_trigger: '.o_opportunity_kanban',
        run: 'click',
    }, {
        trigger: 'button[name="action_schedule_meeting"]',
        run: 'click',
    }, {
        trigger: 'button.dropdownAppointmentLink',
        run: 'click',
    }, {
        trigger: '.o_appointment_button_link:contains("Test AppointmentCRM")',
        run: () => {
            // Patch and ignore write on clipboard in tour as we don't have permissions
            navigator.clipboard.writeText = () => { console.info('Copy in clipboard ignored!') };
            $('.o_appointment_button_link:contains("Test AppointmentCRM")').click();
        },
    }, {
        trigger: '.o_appointment_discard_slots',
        run: () => {
            $('.o_appointment_discard_slots').click();
            // Re-patch the function with the previous writeText
            navigator.clipboard.writeText = oldWriteText;
        },
    }],
});
