import { editComposer, clickSend } from "@im_livechat/../tests/tours/livechat_tour_utils";
import { registry } from "@web/core/registry";

// Set by the test from the website palette: o-color-1 and o-color-2.
const PRIMARY = "rgb(17, 34, 51)";
const WHITE = "rgb(255, 255, 255)";

function hexToRgb(hex) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.trim().substring(i, i + 2), 16));
    return `rgb(${r}, ${g}, ${b})`;
}

function checkColor(label, actual, expected) {
    if (actual !== expected) {
        throw new Error(`${label}: expected ${expected}, got ${actual}`);
    }
}

function checkBubble(bubble, role) {
    const style = getComputedStyle(bubble);
    checkColor(
        `${role} bubble`,
        style.backgroundColor,
        hexToRgb(style.getPropertyValue(`--o-mail-livechat-${role}-bubble-bg`))
    );
}

registry.category("web_tour.tours").add("website_livechat_theme_colors", {
    steps: () => [
        {
            content: "The live chat button has the theme's primary color",
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run() {
                const style = getComputedStyle(this.anchor);
                checkColor("button background", style.backgroundColor, PRIMARY);
                checkColor("button text", style.color, WHITE);
                this.anchor.click();
            },
        },
        {
            content: "The window header has the theme's primary color",
            trigger: ".o-livechat-root:shadow .o-mail-ChatWindow-header",
            run() {
                checkColor("header background", getComputedStyle(this.anchor).backgroundColor, PRIMARY);
            },
        },
        editComposer("Hello, I need help"),
        {
            content: "The send button has the theme's primary color",
            trigger: ".o-livechat-root:shadow .o-mail-Composer button.o-sendMessageActive[aria-label='Send']:enabled",
            async run() {
                // The circle background fades in (`$btn-transition`).
                await Promise.all(
                    this.anchor.getAnimations({ subtree: true }).map((animation) => animation.finished)
                );
                checkColor("send button", getComputedStyle(this.anchor, "::before").backgroundColor, PRIMARY);
                checkColor("send icon", getComputedStyle(this.anchor).color, WHITE);
            },
        },
        clickSend(),
        {
            content: "The bubbles have the colors derived from the theme",
            trigger:
                ".o-livechat-root:shadow .o-mail-ChatWindow:has(.o-mail-Message-bubble.o-green):has(.o-mail-Message-bubble.o-blue)",
            run() {
                checkBubble(this.anchor.querySelector(".o-mail-Message-bubble.o-green"), "primary");
                checkBubble(this.anchor.querySelector(".o-mail-Message-bubble.o-blue"), "secondary");
            },
        },
    ],
});
