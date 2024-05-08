export function back() {
    return {
        content: "go back to the products",
        trigger: ".pos-topheader .back-button",
    };
}
export function inLeftSide(steps) {
    return [
        {
            content: "click review button",
            trigger: ".btn-switchpane.review-button",
            mobile: true,
        },
        ...[steps].flat(),
        { ...back(), mobile: true },
    ];
}

export function negate(selector, parent = "body") {
    return `${parent}:not(:has(${selector}))`;
}
export function negateStep(step) {
    return {
        ...step,
        trigger: negate(step.trigger),
    };
}
export function run(run, content = "run function") {
    return { content, trigger: "body", run };
}
export function refresh() {
    return run(() => window.location.reload(), "refresh page");
}
export function elementDoesNotExist(selector) {
    return {
        content: `Check that element "${selector}" don't exist.`,
        trigger: negate(selector),
        isCheck: true,
    };
}

export function waitForLoading() {
    return [
        {
            content: "waiting for loading to finish",
            trigger: "body:not(:has(.loader))",
            run: function () {},
        },
    ];
}

export function selectButton(name) {
    return {
        content: `Select button ${name}`,
        trigger: `button:contains("${name}")`,
    };
}
