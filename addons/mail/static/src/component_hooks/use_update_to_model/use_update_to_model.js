/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update/use_update';

const { useComponent } = owl.hooks;

/**
 * This hook provides support for binding the onMounted/onPatched hooks to the
 * method of a target record.
 *
 * @param {Object} param0
 * @param {string} param0.methodName Name of the method on the target record.
 * @param {string} param0.modelName Name of the model of the target record.
 * @param {string} param0.propNameAsRecordLocalId Name of the prop of this component
 *  containing the localId of the target record.
 */
export function useUpdateToModel({ methodName, modelName, propNameAsRecordLocalId }) {
    const component = useComponent();
    useUpdate({ func: () => {
        const record = component.env.services.messaging.modelManager.models[modelName].get(component.props[propNameAsRecordLocalId]);
        if (record) {
            record[methodName]();
        }
    } });
}
