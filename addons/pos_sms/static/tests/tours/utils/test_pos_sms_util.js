export function CheckNumber(val) {
    return [
        {
            content: "Check pre-filled partner phone",
            trigger: `.receipt-screen .send-receipt-phone-input:value('${val}')`,
        },
    ];
}
