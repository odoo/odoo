export function send_payment_cancel() {
    return [
        {
            content: "click send button",
            trigger: ".button.send_payment_cancel",
            run: "click",
        },
    ];
}
