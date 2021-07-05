/** @odoo-module **/

import { FieldOne2Many } from 'web.relational_fields';
import fieldRegistry from 'web.field_registry';
import { SubTasksListRenderer } from '../subtasks_list_renderer';

const SubTasksFieldOne2Many = FieldOne2Many.extend({
    /**
    * We want to use our custom renderer for the list.
    *
    * @override
    */
    _getRenderer() {
        if (this.view.arch.tag === 'tree') {
            return SubTasksListRenderer;
        }
        return this._super.apply(...arguments);
    },
});

fieldRegistry.add('subtasks_one2many', SubTasksFieldOne2Many);
