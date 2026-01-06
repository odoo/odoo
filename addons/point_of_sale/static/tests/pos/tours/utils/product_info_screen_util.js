export function productIsAvailable() {
    return {
        trigger: ".section-availability .btn.btn-secondary",
        content: "Verify that the product is available",
    };
}
export function productIsSnoozed() {
    return {
        trigger: ".section-availability .btn.btn-warning",
        content: "Verify that the product is not available anymore",
    };
}
export function clickSnoozeButton() {
    return {
        trigger: ".section-availability .btn",
        content: "Click the snooze button",
        run: "click",
    };
}
export function clickAvailabilitySwitch() {
    return {
        trigger: ".section-availability .form-switch input[type='checkbox']:not(:checked)",
        content: "Click the snooze button",
        run: "click",
    };
}
export function clickSnoozeDuration(button) {
    return {
        trigger: `.btn-group .row label:contains(${button})`,
        content: `Click the ${button} button`,
        run: "click",
    };
}
