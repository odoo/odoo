/* @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';

export class UserMany2OneField extends Many2OneField {

    setup() {
        super.setup();
        this.orm = useService("orm")
        this.actionService = useService("action")
    }

    async updateRecord(values) {
        if (!values[0]) return super.updateRecord(values);
        const data = this.props.record.data;
        const workContactId = data.work_contact_id[0];
        const userData = await this.orm.read("res.users", [values[0]], ["partner_id"]);
        const partnerId = userData?.[0].partner_id?.[0];
        if (workContactId && partnerId != workContactId) {
            this.env.services.action.doAction("base.action_partner_merge", {
                additionalContext: {
                    default_dst_partner_id: partnerId,
                    default_state: 'selection',
                    default_partner_ids: [workContactId, partnerId],

                },
            });
        }
        return super.updateRecord(values);
    }
}
