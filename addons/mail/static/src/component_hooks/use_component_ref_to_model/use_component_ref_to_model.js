/** @odoo-module **/

import { useRefs } from '@mail/component_hooks/use_refs/use_refs';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { clear } from '@mail/model/model_field_command';

const { useComponent } = owl.hooks;

/**
 * This hook provides support for saving the result of (with component) useRefs
 * directly into the field of a record, and appropriately updates it when
 * necessary (props change or destroy).
 *
 * @param {Object} param0
 * @param {string} param0.fieldName Name of the field on the target record.
 * @param {string} param0.modelName Name of the model of the target record.
 * @param {string} param0.propNameAsRecordLocalId Name of the prop of this
 *  component containing the localId of the target record.
 * @param {string} param0.refName Name of the ref on this component.
 */
export function useComponentRefToModel({ fieldName, modelName, propNameAsRecordLocalId, refName }) {
    const component = useComponent();
    const { modelManager } = component.env.services.messaging;
    useRefs();
    useUpdate({
        func: () => {
            const record = modelManager.models[modelName].get(component.props[propNameAsRecordLocalId]);
            if (record) {
                const ref = component.refs[refName];
                record.update({ [fieldName]: ref ? ref : clear() });
            }
        },
    });
    const __destroy = component.__destroy;
    component.__destroy = parent => {
        const record = modelManager.models[modelName].get(component.props[propNameAsRecordLocalId]);
        if (record) {
            record.update({ [fieldName]: clear() });
        }
        __destroy.call(component, parent);
    };
}