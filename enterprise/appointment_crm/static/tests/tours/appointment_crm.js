/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const oldWriteText = browser.navigator.clipboard.writeText;

registry.category("web_tour.tours").add('appointment_crm_meeting_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
        run: 'click',
    },
    {
        trigger: ".o_opportunity_kanban",
    },
    {
        trigger: '.o_kanban_record:contains("Test Opportunity")',
        run: 'click',
    }, {
        trigger: 'button[name="action_schedule_meeting"]',
        run: 'click',
    }, {
        trigger: 'button.dropdownAppointmentLink',
        run: 'click',
    }, {
        trigger: '.o_appointment_button_link:contains("Test AppointmentCRM")',
        async run(helpers) {
            // Patch and ignore write on clipboard in tour as we don't have permissions
            browser.navigator.clipboard.writeText = () => { console.info('Copy in clipboard ignored!') };
            await helpers.click();
        },
    }, {
        trigger: '.o_appointment_discard_slots',
        async run(helpers) {
            // Cleanup the patched clipboard method
            browser.navigator.clipboard.writeText = oldWriteText;

            await helpers.click();
        },
    }],
});
