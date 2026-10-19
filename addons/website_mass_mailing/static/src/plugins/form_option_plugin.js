import { Domain } from "@web/core/domain";
import { patch } from '@web/core/utils/patch';
import { FormOptionPlugin } from "@website/builder/plugins/form/form_option_plugin";

patch(FormOptionPlugin.prototype, {
    /**
     * Adds domain to avoid loading private mailing lists.
     */
    async _fetchFieldRecords({ field }) {
        if (field.name === 'list_ids' && field.relation === 'mailing.list') {
            field.domain = Domain.and([field.domain || [], [['is_public', '=', true]]]).toList();
        }
        return super._fetchFieldRecords(...arguments);
    }
});
