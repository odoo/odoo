import { untrack } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @param {import("./datetimepicker_plugin").DateTimePickerServiceParams} params
 */
export function useDateTimePicker(params) {
    function getInputs() {
        return inputRefs.map((ref) => untrack(ref));
    }

    // Callers driving the picker from a `target` only (no date inputs) omit
    // `inputRefs`.
    const inputRefs = params.inputRefs ?? [];

    return useService("datetime_picker").create(
        // Need original object since 'pickerProps' (or any other param) can be defined
        // as getters
        Object.assign(Object.create(params), { getInputs }),
        { useOwlHooks: true }
    );
}
