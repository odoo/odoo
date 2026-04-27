/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    async _performRPC(route, args) {
        if (args.model === 'documents.document' && args.method === 'get_document_max_upload_limit') {
            return Promise.resolve(67000000);
        }
        return super._performRPC(...arguments);
    },
    /**
     * Override to handle the specific case of model 'documents.document'.
     *
     * @override
     */
    mockSearchPanelSelectRange(model, [fieldName], kwargs) {
        const enableCounters = kwargs.enable_counters || false;
        const fields = ['display_name', 'description', 'folder_id', 'user_permission'];
        const records = this.mockSearchRead('documents.document', [[["type", "=", "folder"]], fields], {});

        let domainImage = new Map();
        if (enableCounters || !kwargs.expand) {
            domainImage = this.mockSearchPanelFieldImage(model, fieldName, { ...kwargs, only_counters: kwargs.expand});
        }

        const valuesRange = new Map();
        for (const record of records) {
            if (enableCounters) {
                record.__count = domainImage.get(record.id) ? domainImage.get(record.id).__count : 0;
            }
            const value = record.folder_id;
            record.folder_id = value && value[0];
            valuesRange.set(record.id, record);
        }
        if (kwargs.enable_counters) {
            this.mockSearchPanelGlobalCounters(valuesRange, 'folder_id');
        }
        return {
            parent_field: 'folder_id',
            values: [...valuesRange.values()],
        };
    },
});
