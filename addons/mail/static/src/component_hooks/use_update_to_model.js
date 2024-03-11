/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';

const { useComponent } = owl;

/**
 * This hook provides support for binding the onMounted/onPatched hooks to the
 * method of a target record.
 *
 * @param {Object} param0
 * @param {string} param0.methodName Name of the method on the target record.
 */
export function useUpdateToModel({ methodName }) {
    const component = useComponent();
    useUpdate({ func: () => {
        component.props.record[methodName]();
    } });
}
