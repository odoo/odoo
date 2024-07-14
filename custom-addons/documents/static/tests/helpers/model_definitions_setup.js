/** @odoo-module **/

import { addModelNamesToFetch } from '@bus/../tests/helpers/model_definitions_helpers';

addModelNamesToFetch([
    'documents.document', 'documents.folder', 'documents.tag', 'documents.share',
    'documents.workflow.rule', 'documents.facet', 'mail.alias',
]);
