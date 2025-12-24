export function clickShipLaterButton() {
    return [
        {
            content: "click ship later button",
            trigger: ".button:contains('Ship Later')",
            run: "click",
        },
        {
            content: "click confirm button",
            trigger: ".btn:contains('Confirm')",
            run: "click",
        },
    ];
}

export function shippingLaterHighlighted() {
    return {
        content: "Shipping later button is highlighted",
        trigger: ".button:contains('Ship Later').highlight",
    };
}
