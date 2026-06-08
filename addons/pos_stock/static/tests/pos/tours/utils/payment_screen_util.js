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

export function setShipLaterDate(date) {
    return [
        {
            content: "click ship later button",
            trigger: ".button:contains('Ship Later')",
            run: "click",
        },
        {
            content: "pick a date",
            trigger: ".modal-body .o_datetime_input",
            run: () => {
                const input = document.querySelector(".modal-body .o_datetime_input");
                input.value = date;
                input.dispatchEvent(new Event("input", { bubbles: true }));
                input.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "click confirm button",
            trigger: ".btn:contains('Confirm')",
            run: "click",
        },
    ];
}
