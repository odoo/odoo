/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { registry } from '@web/core/registry';
import { utils, clearRegistryWithCleanup } from '@web/../tests/helpers/mock_env';

const { prepareRegistriesWithCleanup } = utils;

function makeFakeWebsiteService() {
    return {
        start() {
            return {
                get context() {
                    return {};
                },
                isPublisher() {
                    return true;
                },
            };
        }
    };
}

const serviceRegistry = registry.category('services');
patch(utils, 'website_test_registries', {
    prepareRegistriesWithCleanup() {
        prepareRegistriesWithCleanup(...arguments);
        serviceRegistry.add('website', makeFakeWebsiteService());
        clearRegistryWithCleanup(registry.category('website_systray'));
    },
});
