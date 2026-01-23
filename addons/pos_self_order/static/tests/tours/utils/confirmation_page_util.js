export function isShown() {
    return {
        content: "Confirmation page is shown",
        trigger: ".confirmation-page",
    };
}

export function checkFinalPrice(price) {
    return {
        content: "Check price computed on the backend",
        trigger: `.confirmation-page:contains(Pay at the cashier ${price})`,
    };
}

export function orderNumberShown() {
    return {
        content: "Check if the order number is shown",
        trigger: ".number",
    };
}
