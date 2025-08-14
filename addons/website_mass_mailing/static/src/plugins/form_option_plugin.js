import { patch } from '@web/core/utils/patch';
import { FormOptionPlugin } from "@website/builder/plugins/form/form_option_plugin";

patch(FormOptionPlugin.prototype, {
    /**
     * Adds fieldName as "name" so the "name" field gets fetched instead of the
     * "display_name" field to avoid seeing `(number of contacts)` in the
     * "Subscribe to Newsletter" form editor.
     */
    async _fetchFieldRecords(field) {
        if (field.name === 'list_ids' && field.relation === 'mailing.list') {
            field.fieldName = 'name';
        }
        return super._fetchFieldRecords(...arguments);
    }
});
