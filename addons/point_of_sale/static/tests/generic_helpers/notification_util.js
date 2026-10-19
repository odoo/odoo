export function has(text, type) {
    let trigger = `.o_notification:contains("${text}")`;
    if (type) {
        trigger += `:has(.o_notification_bar.bg-${type})`;
    }
    return {
        content: `Check if there is a notification with text "${text}"`,
        trigger,
    };
}
