export function isShown() {
    return {
        content: "Confirmation page is shown",
        trigger: ".confirmation-page",
    };
}

export function orderNumberShown() {
    return {
        content: "Check if the order number is shown",
        trigger: ".number",
    };
}

export function orderNumberIs(trackingPrefix, trackingNumber) {
    return {
        content: `Check that the order number start with '${trackingPrefix}', and end with number '${trackingNumber}'.`,
        trigger: `span.number`,
        run: function () {
            const span = document.querySelector("span.number");
            const text = span.textContent || "";
            if (!text.startsWith(trackingPrefix) || !text.endsWith(trackingNumber)) {
                throw new Error(
                    `Order number '${text}' does not start with '${trackingPrefix}' and end with '${trackingNumber}'`
                );
            }
        },
    };
}
