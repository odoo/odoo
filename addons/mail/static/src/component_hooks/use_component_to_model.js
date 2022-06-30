/** @odoo-module **/

import { clear } from '@mail/model/model_field_command';

<<<<<<< HEAD
const { onWillUpdateProps, useComponent } = owl;
=======
const { onWillDestroy, onWillRender, onWillUpdateProps, useComponent } = owl;
>>>>>>> 9a2420a6e69... temp

/**
 * This hook provides support for saving the reference of the component directly
 * into the field of a record, and appropriately updates it when necessary
 * (props change or destroy).
 *
 * @param {Object} param0
 * @param {string} param0.fieldName Name of the field on the target record.
 */
export function useComponentToModel({ fieldName }) {
    const component = useComponent();
    component.props.record.update({ [fieldName]: component });
    onWillUpdateProps(nextProps => {
        const currentRecord = component.props.record;
        const nextRecord = nextProps.record;
        if (currentRecord.exists() && currentRecord !== nextRecord) {
            currentRecord.update({ [fieldName]: clear() });
        }
<<<<<<< HEAD
        nextRecord.update({ [fieldName]: component });
=======
        if (nextRecord) {
            nextRecord.update({ [fieldName]: component });
        }
    });
    onWillRender(() => {
        const record = modelManager.models[modelName].get(component.props.localId);
        if (record && !record[fieldName]) {
            // When the record is deleted then created again, its
            // localId can be the same. In this scenario, the Component
            // would not call setup neither willUpdateprops. Therefore,
            // we need to set the component for this new record.
            record.update({ [fieldName]: component });
        }
    });
    onWillDestroy(() => {
        const record = modelManager.models[modelName].get(component.props.localId);
        if (record) {
            record.update({ [fieldName]: clear() });
        }
>>>>>>> 9a2420a6e69... temp
    });
}
