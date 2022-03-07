/** @odoo-module **/

import { clear } from '@mail/model/model_field_command';

const { onWillUpdateProps, useComponent, useRef } = owl.hooks;

/**
 * This hook provides support for saving the result of useRef directly into the
 * field of a record, and appropriately updates it when necessary (props change
 * or destroy).
 *
 * @param {Object} param0
 * @param {string} param0.fieldName Name of the field on the target record.
 * @param {string} param0.modelName Name of the model of the target record.
 * @param {string} param0.propNameAsRecordLocalId Name of the prop of this
 *  component containing the localId of the target record.
 * @param {string} param0.refName Name of the t-ref on this component.
 */
export function useRefToModel({ fieldName, modelName, propNameAsRecordLocalId, refName }) {
    const component = useComponent();
    const { modelManager } = component.env.services.messaging;
    const record = modelManager.models[modelName].get(component.props[propNameAsRecordLocalId]);
    const ref = useRef(refName);
    if (record) {
        record.update({ [fieldName]: ref });
    }
    onWillUpdateProps(nextProps => {
        const currentRecord = modelManager.models[modelName].get(component.props[propNameAsRecordLocalId]);
        const nextRecord = modelManager.models[modelName].get(nextProps[propNameAsRecordLocalId]);
        if (currentRecord && currentRecord !== nextRecord) {
            currentRecord.update({ [fieldName]: clear() });
        }
        if (nextRecord) {
            nextRecord.update({ [fieldName]: ref });
        }
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
