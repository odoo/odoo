/** @odoo-module **/

import { addModelNamesToFetch } from '@bus/../tests/helpers/model_definitions_helpers';

addModelNamesToFetch([
    'documents.document', 'documents.tag', 'mail.alias', 'mail.alias.domain', 'ir.actions.server', 'ir.embedded.actions',
]);
