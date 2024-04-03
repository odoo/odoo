/** @odoo-module **/

import { clear } from '@mail/model/model_field_command';

const { onWillUpdateProps, useComponent, useRef } = owl;

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
        nextRecord.update({ [fieldName]: ref });
    });
}
