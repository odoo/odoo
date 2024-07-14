/** @odoo-module **/

import { Domain } from '@web/core/domain';
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
     * Mocks the '_get_models' method of the model 'documents.document'.
     *
     * @param {string} model
     * @param {any[]} domain
     */
    _mockGetModels(model, domain) {
        const notAFile = [];
        const notAttached = [];
        const models = [];
        const groups = this.mockReadGroup(model, {
            domain: domain,
            fields: ['res_model'],
            groupby: ['res_model'],
        });
        for (const group of groups) {
            if (!group.res_model) {
                notAFile.push({
                    id: group.res_model,
                    display_name: "Not a file",
                    __count: group.res_model_count,
                });
            } else if (group.res_model === 'documents.document') {
                notAttached.push({
                    id: group.res_model,
                    display_name: "Not attached",
                    __count: group.res_model_count,
                });
            } else {
                const { res_model_name } = this.models['documents.document'].records.find(
                    record => record.res_model === group.res_model
                );
                models.push({
                    id: group.res_model,
                    display_name: res_model_name,
                    __count: group.res_model_count,
                });
            }
        }
        const sorted = models.sort(({ display_name: a }, { display_name: b }) => {
            return a > b ? 1 : a < b ? -1 : 0;
        });
        return [...sorted, ...notAttached, ...notAFile];
    },
    /**
     * Override to handle the specific case of model 'documents.document'.
     *
     * @override
     */
    mockSearchPanelSelectRange(model, [fieldName], kwargs) {
        if (model === 'documents.document' && fieldName === 'folder_id') {
            const enableCounters = kwargs.enable_counters || false;
            const fields = ['display_name', 'description', 'parent_folder_id', 'has_write_access'];
            const records = this.mockSearchRead('documents.folder', [[], fields], {});

            let domainImage = new Map();
            if (enableCounters || !kwargs.expand) {
                domainImage = this.mockSearchPanelFieldImage(model, fieldName, { ...kwargs, only_counters: kwargs.expand});
            }

            const valuesRange = new Map();
            for (const record of records) {
                if (enableCounters) {
                    record.__count = domainImage.get(record.id) ? domainImage.get(record.id).__count : 0;
                }
                const value = record.parent_folder_id;
                record.parent_folder_id = value && value[0];
                valuesRange.set(record.id, record);
            }
            if (kwargs.enable_counters) {
                this.mockSearchPanelGlobalCounters(valuesRange, 'parent_folder_id');
            }
            return {
                parent_field: 'parent_folder_id',
                values: [...valuesRange.values()],
            };
        }
        return super.mockSearchPanelSelectRange(...arguments);
    },
    /**
     * Override to handle the specific case of model 'documents.document'.
     *
     * @override
     */
    mockSearchPanelSelectMultiRange(model, [fieldName], kwargs) {
        const searchDomain = kwargs.search_domain || [];
        const categoryDomain = kwargs.category_domain || [];
        const filterDomain = kwargs.filter_domain || [];

        if (model === 'documents.document') {
            if (fieldName === 'tag_ids') {
                const folderId = categoryDomain.length ? categoryDomain[0][2] : false;
                const domain = Domain.combine([
                    searchDomain,
                    categoryDomain,
                    filterDomain,
                    [[fieldName, '!=', false]],
                ], "AND").toList();
                const values = folderId ? this._mockDocumentsTag_GetTags(domain, folderId) : [];
                return { values };
            } else if (fieldName === 'res_model') {
                let domain = Domain.combine([searchDomain, categoryDomain], "AND").toList();
                const modelValues = this._mockGetModels(model, domain);
                if (filterDomain) {
                    domain = Domain.combine([
                        searchDomain,
                        categoryDomain,
                        filterDomain,
                    ], "AND").toList();
                    const modelCount = {};
                    for (const { id, __count } of this._mockGetModels(model, domain)) {
                        modelCount[id] = __count;
                    }
                    modelValues.forEach(m => m.__count = modelCount[m.id] || 0);
                }
                return {values: modelValues, };
            }
        }
        return super.mockSearchPanelSelectMultiRange(...arguments);
    },
});
