/** @odoo-module **/

import { FieldOne2Many } from 'web.relational_fields';
import FieldRegistry from 'web.field_registry';

const ChatbotScriptStepOne2Many = FieldOne2Many.extend({

    /**
     * _render override that removes the sortable options on all columns.
     *
     * Indeed, we want to force the sorting by the 'sequence' field (otherwise the script will
     * make no sense).
     *
     * @override
     * @private
     */
    _render: function () {
        this._super(...arguments).then(() => {
            this.$('.o_column_sortable').removeClass('o_column_sortable');
        });
    },

});

FieldRegistry.add('chatbot_script_step_widget', ChatbotScriptStepOne2Many);
