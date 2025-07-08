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
