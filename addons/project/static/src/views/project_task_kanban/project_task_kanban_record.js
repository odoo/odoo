/* @odoo-module */

import { Record } from '@web/views/relational_model';

export class ProjectTaskRecord extends Record {
    async _applyChanges(changes) {
        const value = changes.personal_stage_type_ids;
        if (value && Array.isArray(value) && value.length === 1) {
            delete changes.personal_stage_type_ids;
            changes.personal_stage_type_id = value;
        }
        await super._applyChanges(changes);
    }
}
