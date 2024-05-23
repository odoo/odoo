export function isShown() {
    return {
        content: "Confirmation page is shown",
        trigger: ".confirmation-page",
        run: () => {},
    };
}

export function orderNumberShown() {
    return {
        content: "Check if the order number is shown",
        trigger: ".number",
        run: () => {},
    };
}
