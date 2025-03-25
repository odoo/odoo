import { queryFirst } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
window.queryFirst = queryFirst;
function getSendFirstMessageAndResetSteps(containerSelector) {
    return [
        {
            trigger: `${containerSelector} .o-mail-Composer-input`,
            run: "edit Hello!",
        },
        {
            trigger: `${containerSelector} .o-mail-Composer-input`,
            run: "press Enter",
        },
        {
            trigger: `${containerSelector} .o-mail-Message-body:contains("Hello!")`,
            async run() {
                await odoo.__WOWL_DEBUG__.root.env.services["mail.store"].reset();
            },
        },
    ];
}
function getAfterResetSteps(containerSelector) {
    // Execute basic actions after store reset to ensure that the basic functionalities
    // are still working as expected: Send/Edit message, Add/Remove reactio
    return [
        {
            trigger: `${containerSelector} .o-mail-Composer-input`,
            run: "click",
        },
        {
            trigger: `${containerSelector} .o-mail-Composer-input`,
            run: "edit Hello again!",
        },
        {
            trigger: `${containerSelector} .o-mail-Composer-input`,
            run: "press Enter",
        },
        {
            trigger: `${containerSelector} .o-mail-Message-textContent:contains(Hello again!):not(:has(.o-mail-Message-pendingProgress))`,
        },
        {
            trigger: `${containerSelector} .o-mail-Message:contains(Hello again!) [title='Expand']:not(:visible)`,
            run: "click",
        },
        {
            trigger: `[title='Edit']`,
            run: "click",
        },
        {
            trigger: `${containerSelector} .o-mail-Composer-input`,
            run: "edit Goodbye!",
        },
        {
            trigger: `${containerSelector} .o-mail-Composer-input`,
            run: "press Enter",
        },
        {
            trigger: `${containerSelector} .o-mail-Message-textContent:contains(Hello!)`,
            run: "hover && click .o-mail-Message [title='Add a Reaction']",
        },
        {
            trigger: `.o-mail-QuickReactionMenu-emojiPicker`,
            run: "click",
        },
        {
            trigger: `.o-EmojiPicker .o-Emoji:contains('🙂')`,
            run: "click",
        },
        {
            content: "Remove reaction",
            trigger: `${containerSelector} .o-mail-MessageReaction:contains('🙂')`,
            run: "click",
        },
        {
            trigger: `${containerSelector} .o-mail-Message:not(:has(.o-mail-MessageReaction))`,
        },
    ];
}

registry.category("web_tour.tours").add("discuss.store_reset_in_discuss", {
    steps: () => [
        ...getSendFirstMessageAndResetSteps(
            ".o-mail-Discuss-content:has(.o-mail-Discuss-threadName[title='MyChannel'])"
        ),
        ...getAfterResetSteps(
            ".o-mail-Discuss-content:has(.o-mail-Discuss-threadName[title='MyChannel'])"
        ),
    ],
});

registry.category("web_tour.tours").add("discuss.store_reset_with_chat_windows", {
    steps: () => [
        {
            trigger: ".o-mail-DiscussSystray-class .fa-comments",
            run: "click",
        },
        {
            trigger: ".o-mail-NotificationItem:contains('MyChannel')",
            run: "click",
        },
        ...getSendFirstMessageAndResetSteps(".o-mail-ChatWindow:contains('MyChannel')"),
        ...getAfterResetSteps(".o-mail-ChatWindow:contains('MyChannel')"),
    ],
});
