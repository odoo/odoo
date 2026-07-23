import { useService } from "@web/core/utils/hooks";
import { resolveRefEl } from "@web/core/utils/ref_utils";

/**
 * @param {import("./datetimepicker_service").DateTimePickerServiceParams} params
 */
export function useDateTimePicker(params) {
    function getInputs() {
        return inputRefs.map((ref) => resolveRefEl(ref));
    }

    // Callers provide Owl 3 signal refs (or legacy refs) through `inputRefs`.
    // Callers driving the picker from a `target` only (no date inputs) omit it.
    const inputRefs = params.inputRefs ?? [];

    return useService("datetime_picker").create(
        // Need original object since 'pickerProps' (or any other param) can be defined
        // as getters
        Object.assign(Object.create(params), { getInputs }),
        { useOwlHooks: true }
    );
}
