import { registry } from "@web/core/registry";
import { inputFiles } from "@web/../tests/utils";

// The tour is ran twice, ensure the correct message is always targetted.
const messageSelector = ".o-mail-Message:has(.o-mail-Message-body:contains('cheese'))";
const editedMessageSelector = ".o-mail-Message:has(.o-mail-Message-body:contains('vegetables'))";

registry.category("web_tour.tours").add("discuss_channel_public_tour.js", {
    steps: () => [
        {
            trigger: ".o-mail-Discuss",
        },
        {
            trigger: ".o-mail-Thread",
            run() {
                if (!window.location.pathname.startsWith("/discuss/channel")) {
                    console.error("Channel secret token is still present in URL.");
                }
                const errors = odoo.loader.findErrors();
                if (Object.keys(errors).length) {
                    console.error("Couldn't load all JS modules.", errors);
                }
                document.body.classList.add("o_discuss_channel_public_modules_loaded");
                if (
                    document.title !== document.querySelector(".o-mail-Discuss-threadName")?.value
                ) {
                    console.error("Tab title should match conversation name.");
                }
            },
        },
        {
            trigger: ".o_discuss_channel_public_modules_loaded",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "edit cheese",
        },
        {
            trigger: ".o-mail-Composer button[aria-label='Attach files']",
            async run() {
                const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
                await inputFiles(".o-mail-Composer-coreMain .o_input_file", [text]);
            },
        },
        {
            trigger: ".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt)",
        },
        {
            trigger: ".o-mail-Composer button[aria-label='Attach files']",
            async run() {
                await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
                    new File(
                        [
                            await (
                                await fetch(
                                    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIW2P4v5ThPwAG7wKklwQ/bwAAAABJRU5ErkJggg=="
                                )
                            ).blob(),
                        ],
                        "image.png",
                        { type: "image/png" }
                    ),
                ]);
            },
        },
        {
            trigger: '.o-mail-AttachmentImage:not(.o-isUploading)[title="image.png"]',
            async run() {
                const store = odoo.__WOWL_DEBUG__.root.env.services["mail.store"];
                if (store.self.type === "guest") {
                    const src = this.anchor.querySelector("img").src;
                    const token = store.Attachment.get(
                        (src.match("/web/image/([0-9]+)") || []).at(-1)
                    )?.access_token;
                    if (!(token && src.includes(`access_token=${token}`))) {
                        throw new Error("Access token of the attachment isn't correct.");
                    }
                }
            },
        },
        {
            trigger: ".o-mail-Composer-send:enabled",
            run: "click",
        },
        {
            trigger: `${messageSelector}[data-persistent]`,
        },
        {
            trigger: `${messageSelector} .o-mail-AttachmentCard:contains("text.txt")`,
        },
        {
            trigger: messageSelector,
            run: `hover && click ${messageSelector} [title='Add a Reaction']`,
        },
        {
            trigger: ".o-EmojiPicker .o-Emoji:contains('🙂')",
            run: "click",
        },
        {
            trigger: `${messageSelector} .o-mail-MessageReaction:contains('🙂')`,
            run: "click",
        },
        {
            trigger: `${messageSelector}:not(:has(.o-mail-MessageReaction:contains('🙂')))`,
        },
        {
            trigger: `${messageSelector}`,
            run: `hover && click ${messageSelector} [title='Expand']`,
        },
        {
            trigger: `.o-mail-Message-moreMenu [title='Edit'], ${messageSelector} [title='Edit']`,
            run: "click",
        },
        {
            trigger: ".o-mail-Message .o-mail-Composer-input",
            run: "edit vegetables",
        },
        {
            trigger: ".o-mail-Message button[aria-label='Attach files']",
            async run() {
                const extratxt = new File(["hello 2"], "extra.txt", { type: "text/plain" });
                await inputFiles(".o-mail-Message .o_input_file", [extratxt]);
            },
        },
        {
            trigger:
                ".o-mail-Message .o-mail-Composer .o-mail-AttachmentCard:not(.o-isUploading):contains(extra.txt)",
        },
        {
            trigger: ".o-mail-Message a:contains(save)",
            run: "click",
        },
        {
            trigger: editedMessageSelector,
        },
        {
            trigger: `${editedMessageSelector} .o-mail-AttachmentCard:contains("text.txt")`,
        },
        {
            trigger: `${editedMessageSelector} .o-mail-AttachmentCard:contains("extra.txt")`,
        },
        {
            trigger: `${editedMessageSelector} .o-mail-AttachmentCard:contains("extra.txt") .o-mail-AttachmentCard-unlink`,
            run: "click",
        },
        {
            trigger: ".modal:contains(Confirmation) .btn:contains(Ok)",
            run: "click",
        },
        {
            trigger: `${editedMessageSelector}:not(:has(.o-mail-AttachmentCard:contains("extra.txt")))`,
        },
        {
            trigger: "button[title='Search Messages']",
            run: "click",
        },
        {
            trigger: ".o_searchview_input",
            run: "edit text.txt",
        },
        {
            trigger: "button[aria-label='Search button']",
            run: "click",
        },
        {
            trigger: `.o-mail-SearchMessagesPanel ${editedMessageSelector} .o-mail-AttachmentCard:contains("text.txt")`,
        },
    ],
});
