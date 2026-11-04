/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import options from '@web_editor/js/editor/snippets.options';

const websiteMassMailingFetchFieldRecords = {
    /**
    * Adds fieldName as "name" so the "name" field gets fetched instead
    * of the "display_name" field to avoid seeing (number of contacts) in
    * the "Subscribe to Newsletter" form editor.
    */
    async _fetchFieldRecords(field) {
        if (field.name === 'list_ids' && field.relation === 'mailing.list') {
            field.fieldName = 'name';
        }
        return super._fetchFieldRecords(...arguments);
    }
};

patch(options.registry.WebsiteFormEditor.prototype, websiteMassMailingFetchFieldRecords);
patch(options.registry.WebsiteFieldEditor.prototype, websiteMassMailingFetchFieldRecords);
