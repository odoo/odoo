/** @odoo-module */

import { testEnvServices } from '@web/../tests/legacy/helpers/test_services';

Object.assign(testEnvServices, {
    knowledgeService: {
        pushToValidateWithHtmlField: () => {},
        popToValidateWithHtmlField: () => {},
        registerRecord: () => {},
        unregisterRecord: () => {},
        getAvailableRecordWithChatter: () => {},
        getAvailableRecordWithHtmlField: () => {},
        getRecords: () => new Set(),
    }
});
