/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import 'website.form_editor'
import options from 'web_editor.snippets.options';

/**
 * add fieldName as "name" so the "name" field gets fetched instead
 * of the "display_name" field to avoid seeing (number of contacts) in the 
 * "Subscribe to Newsletter" form editor
 */
function websiteMassMailingFetchFieldRecords(){
    return{
            async _fetchFieldRecords(field) {
                if (field.name === 'list_ids') {
                    field.fieldName = 'name';  
                }
                return await this._super(field);  
            }
    }
}

patch(options.registry.WebsiteFormEditor.prototype, "website_mass_mailing_website_form_editor", websiteMassMailingFetchFieldRecords());
patch(options.registry.WebsiteFieldEditor.prototype, "website_mass_mailing_website_field_editor", websiteMassMailingFetchFieldRecords());