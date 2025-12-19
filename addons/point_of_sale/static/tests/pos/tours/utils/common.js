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

export function expectActionTarget(expectedTarget) {
    const actionService = odoo.__WOWL_DEBUG__.root.actionService;
    const original = actionService.doAction;

    return new Promise((resolve, reject) => {
        actionService.doAction = async (action, options) => {
            try {
                if (action.target !== expectedTarget) {
                    throw new Error(`Expected target "${expectedTarget}", got "${action.target}"`);
                }
                resolve();
            } catch (err) {
                reject(err);
            } finally {
                actionService.doAction = original;
            }
            return original(action, options);
        };
    });
}
