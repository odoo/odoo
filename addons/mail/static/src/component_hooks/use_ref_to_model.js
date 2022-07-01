/** @odoo-module **/

import { clear } from '@mail/model/model_field_command';

<<<<<<< HEAD
const { onWillUpdateProps, useComponent, useRef } = owl;
=======
const { onWillDestroy, onWillRender, onWillUpdateProps, useComponent, useRef } = owl;
>>>>>>> 38c17769e8f... temp

/**
 * This hook provides support for saving the result of useRef directly into the
 * field of a record, and appropriately updates it when necessary (props change
 * or destroy).
 *
 * @param {Object} param0
 * @param {string} param0.fieldName Name of the field on the target record.
 * @param {string} param0.refName Name of the t-ref on this component.
 */
export function useRefToModel({ fieldName, refName }) {
    const component = useComponent();
    const ref = useRef(refName);
    component.props.record.update({ [fieldName]: ref });
    onWillUpdateProps(nextProps => {
        const currentRecord = component.props.record;
        const nextRecord = nextProps.record;
        if (currentRecord.exists() && currentRecord !== nextRecord) {
            currentRecord.update({ [fieldName]: clear() });
        }
<<<<<<< HEAD
        nextRecord.update({ [fieldName]: ref });
=======
        if (nextRecord) {
            nextRecord.update({ [fieldName]: ref });
        }
    });
    onWillRender(() => {
        const record = modelManager.models[modelName].get(component.props.localId);
        if (record && !record[fieldName]) {
            // When the record is deleted then created again, its
            // localId can be the same. In this scenario, the Component
            // would not call setup neither willUpdateprops. Therefore,
            // we need to set the ref for this new record.
            record.update({ [fieldName]: ref });
        }
    });
    onWillDestroy(() => {
        const record = modelManager.models[modelName].get(component.props.localId);
        if (record) {
            record.update({ [fieldName]: clear() });
        }
>>>>>>> 38c17769e8f... temp
    });
}
