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
        nextRecord.update({ [fieldName]: component });
    });
}
