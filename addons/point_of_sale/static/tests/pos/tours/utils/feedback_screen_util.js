export function isShown() {
    return {
        content: "feedback screen is shown",
        trigger: ".feedback-screen",
    };
}

export function clickScreen() {
    return {
        content: "click on feedback screen",
        trigger: ".feedback-screen",
        run: "click",
    };
}

export function isSuccess() {
    return {
        content: "feedback screen shows success state with icon, Amount Paid and amount",
        trigger: ".feedback-screen:has(svg):has(.amount-paid):has(.amount)",
    };
}
