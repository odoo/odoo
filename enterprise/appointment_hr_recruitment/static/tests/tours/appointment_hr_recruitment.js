/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const oldWriteText = browser.navigator.clipboard.writeText;

registry.category("web_tour.tours").add('appointment_hr_recruitment_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
        run: 'click',
    }, {
        trigger: '.o_kanban_record:contains("Test Job")',
        run: 'click',
    }, {
        trigger: '.o_kanban_record:contains("Test Applicant")',
        run: 'click',
    },{
        trigger: 'button[name="action_create_meeting"]',
        run: 'click',
    }, {
        trigger: 'button.dropdownAppointmentLink',
        run: 'click',
    }, {
        trigger: '.o_appointment_button_link:contains("Test AppointmentHrRecruitment")',
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
