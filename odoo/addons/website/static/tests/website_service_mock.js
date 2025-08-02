/** @odoo-module */

import { patch } from "@web/core/utils/patch";
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
                get isRestrictedEditor() {
                    return true;
                },
                get hasMultiWebsites() {
                    return true;
                },
                async fetchUserGroups() {},
            };
        }
    };
}

function makeFakeWebsiteCustomMenusService() {
    return {
        start() {
            return {
                get() {},
                open() {},
                addCustomMenus(sections) {
                    return sections;
                },
            };
        }
    };
}

const serviceRegistry = registry.category('services');
patch(utils, {
    prepareRegistriesWithCleanup() {
        prepareRegistriesWithCleanup(...arguments);
        serviceRegistry.add('website', makeFakeWebsiteService());
        serviceRegistry.add('website_custom_menus', makeFakeWebsiteCustomMenusService());
        clearRegistryWithCleanup(registry.category('website_systray'));
    },
});
