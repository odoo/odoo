import { useService } from "@web/core/utils/hooks";
import { useRef } from "@web/owl2/utils";
import { resolveRefEl } from "@web/core/utils/ref_utils";

/**
 * @param {import("./datetimepicker_service").DateTimePickerServiceParams} params
 */
export function useDateTimePicker(params) {
    function getInputs() {
        return inputRefs.map((ref) => resolveRefEl(ref));
    }

    // Callers may provide Owl 3 signal refs (or legacy refs) through `inputRefs`.
    // Fall back to the legacy `t-custom-ref` names for callers not passing them.
    const inputRefs = params.inputRefs ?? [useRef("start-date"), useRef("end-date")];

    return useService("datetime_picker").create(
        // Need original object since 'pickerProps' (or any other param) can be defined
        // as getters
        Object.assign(Object.create(params), { getInputs }),
        { useOwlHooks: true }
    );
}
