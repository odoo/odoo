/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { Component, onWillStart } from '@odoo/owl';

export class AppointmentTypeActionHelper extends Component {
    static template = 'appointment.AppointmentTypeActionHelper';
    static props = {};

    setup() {
        this.orm = useService('orm');
        this.action = useService('action');

        onWillStart(async () => {
            this.appointmentTypeTemplateData = await this.orm.call(
                'appointment.type',
                'get_appointment_type_templates_data',
                []
            );
        });
    }

    async onTemplateClick(templateInfo) {
        const action = await this.orm.call(
            'appointment.type',
            'action_setup_appointment_type_template',
            [templateInfo.template_key],
        );
        this.action.doAction(action);
    }
};
