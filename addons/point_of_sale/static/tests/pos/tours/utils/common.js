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
