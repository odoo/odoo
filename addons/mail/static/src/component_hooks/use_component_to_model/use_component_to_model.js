/** @odoo-module **/

import { clear } from '@mail/model/model_field_command';

const { onWillUpdateProps, useComponent } = owl;

/**
 * This hook provides support for saving the reference of the component directly
 * into the field of a record, and appropriately updates it when necessary
 * (props change or destroy).
 *
 * @param {Object} param0
 * @param {string} param0.fieldName Name of the field on the target record.
 * @param {string} param0.modelName Name of the model of the target record.
 */
export function useComponentToModel({ fieldName, modelName }) {
    const component = useComponent();
    const { modelManager } = component.env.services.messaging;
    const record = modelManager.models[modelName].get(component.props.localId);
    if (record) {
        record.update({ [fieldName]: component });
    }
    onWillUpdateProps(nextProps => {
        const currentRecord = modelManager.models[modelName].get(component.props.localId);
        const nextRecord = modelManager.models[modelName].get(nextProps.localId);
        if (currentRecord && currentRecord !== nextRecord) {
            currentRecord.update({ [fieldName]: clear() });
        }
        if (nextRecord) {
            nextRecord.update({ [fieldName]: component });
        }
    });
    const __render = component.__render;
    component.__render = fiber => {
        const record = modelManager.models[modelName].get(component.props.localId);
        if (record && !record[fieldName]) {
            // When the record is deleted then created again, its
            // localId can be the same. In this scenario, the Component
            // would not call setup neither willUpdateprops. Therefore,
            // we need to set the component for this new record.
            record.update({ [fieldName]: component });
        }
        __render.call(component, fiber);
    };
    const __destroy = component.__destroy;
    component.__destroy = parent => {
        const record = modelManager.models[modelName].get(component.props.localId);
        if (record) {
            record.update({ [fieldName]: clear() });
        }
        __destroy.call(component, parent);
    };
}
