/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { registry } from '@web/core/registry';
import { utils } from '@web/../tests/helpers/mock_env';

const { prepareRegistriesWithCleanup } = utils;

function makeFakeKnowledgeCommandsService() {
    return {
        start() {
            return {
                setCommandsRecordInfo() {},
                getCommandsRecordInfo() { return null; },
                getBreadcrumbsIdentifier() { return []; },
                isRecordCompatibleWithMacro() {},
                unregisterCommandsRecordInfo() {},
                setPendingBehaviorBlueprint() {},
                popPendingBehaviorBlueprint() {},
            };
        }
    };
}

function makeFakeKnowledgeEmbedsFiltersService() {
    return {
        start() {
            return {
                saveFilters: () => {},
                applyFilter: () => {}
            };
        }
    };
}

const serviceRegistry = registry.category('services');
patch(utils, {
    prepareRegistriesWithCleanup() {
        prepareRegistriesWithCleanup(...arguments);
        serviceRegistry.add('knowledgeCommandsService', makeFakeKnowledgeCommandsService());
        serviceRegistry.add('knowledgeEmbedViewsFilters', makeFakeKnowledgeEmbedsFiltersService());
    },
});
