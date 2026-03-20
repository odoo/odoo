import { clickSendButton } from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";

export function CheckNumber(val) {
    return [
        ...clickSendButton(),
        {
            content: "Check pre-filled partner phone",
            trigger: `.send-receipt-phone-input:value('${val}')`,
        },
    ];
}
