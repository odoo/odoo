import { onWillDestroy, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {import("./datetimepicker_service").DateTimePickerServiceParams & {
 *  endDateRefName?: string;
 *  startDateRefName?: string;
 * }} DateTimePickerHookParams
 */

/**
 * @param {DateTimePickerHookParams} params
 */
export function useDateTimePicker(params) {
    function getInputs() {
        return inputRefs.map((ref) => ref.el);
    }

    const inputRefs = [
        useRef(params.startDateRefName || "start-date"),
        useRef(params.endDateRefName || "end-date"),
    ];

    // Need original object since 'pickerProps' (or any other param) can be defined
    // as getters
    const serviceParams = Object.assign(Object.create(params), {
        getInputs,
        useOwlHooks: true,
    });

    const picker = useService("datetime_picker").create(serviceParams);
    onWillDestroy(() => {
        picker.disable();
    });
    return picker;
}
