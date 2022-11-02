/** @odoo-module **/

export function makeMultiTabToLegacyEnv(legacyEnv) {
    return {
        dependencies: ['multi_tab'],
        start(_, { multi_tab }) {
            legacyEnv.services['multi_tab'] = multi_tab;
        },
    };
}
