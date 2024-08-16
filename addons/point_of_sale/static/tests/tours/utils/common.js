export function back() {
    return {
        content: "go back to the products",
        trigger: ".actionpad .back-button",
        run: "click",
    };
}
export function inLeftSide(steps) {
    return [
        {
            isActive: ["mobile"],
            content: "click review button",
            trigger: ".btn-switchpane.review-button",
            run: "click",
        },
        ...[steps].flat(),
        { ...back(), isActive: ["mobile"] },
    ];
}

export function negate(selector, parent = "body") {
    return `${parent}:not(:has(${selector}))`;
}
export function negateStep(step) {
    return {
        ...step,
        content: `Check that: ---${step.content}--- is not true`,
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
    };
}

export function waitForLoading() {
    return [
        {
            content: "waiting for loading to finish",
            trigger: "body:not(:has(.loader))",
        },
    ];
}

export function selectButton(name) {
    return {
        content: `Select button ${name}`,
        trigger: `button:contains("${name}")`,
        run: "click",
    };
}
