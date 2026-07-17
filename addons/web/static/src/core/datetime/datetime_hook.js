import { onPatched, onWillRender, onWillUnmount, useEffect, useRef } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

/**
 * @param {import("./datetimepicker_service").DateTimePickerHookParams} hookParams
 */
export function useDateTimePicker(hookParams) {
    const datetimePicker = useService("datetime_picker");
    if (typeof hookParams.target === "string") {
        const target = useRef(hookParams.target);
        Object.defineProperty(hookParams, "target", {
            get() {
                return target.el;
            },
        });
    }
    const inputRefs = [useRef("start-date"), useRef("end-date")];
    if (!hookParams.createPopover) {
        hookParams.createPopover = usePopover;
    }
    const getInputs = () => inputRefs.map((ref) => ref?.el);
    const { computeBasePickerProps, state, open, focusIfNeeded, enable, commitValue, disableApply } =
        datetimePicker.create(hookParams, getInputs);
    // Closing the popover applies the pending value, and `create` above already
    // registered an `onWillUnmount` closing it (through `usePopover`). Owl calls
    // these callbacks in reverse registration order, so registering this one
    // afterwards makes it run first: an owner that is going away no longer applies
    // its pending value, which would otherwise reach a destroyed component.
    onWillUnmount(disableApply);
    onWillRender(computeBasePickerProps);
    useEffect(enable, getInputs);

    // Note: this `onPatched` callback must be called after the `useEffect` since
    // the effect may change input values that will be selected by the patch callback.
    onPatched(focusIfNeeded);
    return { state, open, commitValue };
}
