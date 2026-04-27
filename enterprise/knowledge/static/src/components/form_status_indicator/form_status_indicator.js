/** @odoo-module **/

import { FormStatusIndicator } from "@web/views/form/form_status_indicator/form_status_indicator";

/**
 * This extension of the FormStatusIndicator is used to add a new indicator to the ones that already
 * exists. This new icon is used in the same way as the icon in Google Docs => indicate that all changes
 * have been committed to the DB.
 */
export class KnowledgeFormStatusIndicator extends FormStatusIndicator {
    static template = 'knowledge.FormStatusIndicator';
}
