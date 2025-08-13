import { registry } from "@web/core/registry";
import { contains, click, inputFiles } from "@web/../tests/utils";

registry.category("web_tour.tours").add("discuss_channel_public_tour.js", {
    steps: () => [
        {
            trigger: ".o-mail-Discuss",
        },
        {
            content: "Check that we are on channel page",
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
                    !document.title.includes(
                        document.querySelector(".o-mail-Discuss-threadName")?.value
                    )
                ) {
                    console.error(
                        `Tab title should match conversation name. Got "${
                            document.title
                        }" instead of "${
                            document.querySelector(".o-mail-Discuss-threadName")?.value
                        }".`
                    );
                }
            },
        },
        {
            content: "Wait for all modules loaded check in previous step",
            trigger: ".o_discuss_channel_public_modules_loaded",
        },
        {
            content: "Write something in composer",
            trigger: ".o-mail-Composer-input",
            run: "edit cheese",
        },
        { trigger: ".o-mail-Composer button[title='More Actions']", run: "click" },
        {
            content: "Add a text file in composer",
            trigger: ".dropdown-item:contains('Attach Files')",
            async run() {
                const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
                await inputFiles(".o-mail-Composer .o_input_file", [text]);
            },
        },
        {
            trigger: ".o-mail-AttachmentCard:not(.o-isUploading)", // waiting the attachment to be uploaded
        },
        {
            content: "Check the text attachment is listed",
            trigger: '.o-mail-AttachmentCard[title="text.txt"]',
        },
        {
            content: "Add an image file in composer",
            trigger: ".dropdown-item:contains('Attach Files')",
            async run() {
                await inputFiles(".o-mail-Composer .o_input_file", [
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
            trigger: ".o-mail-AttachmentImage:not(.o-isUploading)",
        },
        {
            content: "Check the image attachment is listed",
            trigger: '.o-mail-AttachmentImage[title="image.png"]',
            async run() {
                /** @type {import("models").Store} */
                const store = odoo.__WOWL_DEBUG__.root.env.services["mail.store"];
                if (store.self.type === "guest") {
                    const src = this.anchor.querySelector("img").src;
                    const token = store["ir.attachment"].get(
                        (src.match("/web/image/([0-9]+)") || []).at(-1)
                    )?.raw_access_token;
                    if (!(token && src.includes(`access_token=${token}`))) {
                        throw new Error("Access token of the attachment isn't correct.");
                    }
                }
            },
        },
        { trigger: ".o-mail-Composer-input", run: "click" }, // focus
        {
            content: "Send message",
            trigger: ".o-mail-Composer:has(button[title='Send']:enabled) .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-Message-body:contains("cheese")',
        },
        {
            content: "Check message contains the attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentCard:contains("text.txt")',
        },
        {
            trigger: ".o-mail-Message[data-persistent]:contains(cheese)",
            run: "hover && click .o-mail-Message:contains(cheese) [title='Add a Reaction']",
        },
        {
            trigger: ".o-mail-QuickReactionMenu",
            run: () => click("[title='Toggle Emoji Picker']"),
        },
        {
            trigger: ".o-EmojiPicker .o-Emoji:contains('🙂')",
            run: "click",
        },
        {
            content: "Remove reaction",
            trigger: ".o-mail-MessageReaction:contains('🙂')",
            run: "click",
        },
        {
            trigger: ".o-mail-Message:not(:has(.o-mail-MessageReaction:contains('🙂')))",
        },
        {
            content: "Click on more menu",
            trigger: ".o-mail-Message[data-persistent]:contains(cheese)",
            run: "hover && click .o-mail-Message:contains(cheese) [title='Expand']",
        },
        {
            content: "Click on edit",
            trigger: ".o-mail-Message-moreMenu [title='Edit'], .o-mail-Message [title='Edit']",
            run: "click",
        },
        {
            content: "Edit message",
            trigger: ".o-mail-Message .o-mail-Composer-input",
            run: "edit vegetables",
        },
        {
            content: "Add one more file in composer",
            trigger: ".o-mail-Message .o-mail-Composer button[title='More Actions']",
            run: "click",
        },
        {
            content: "Add one more file in composer",
            trigger: ".dropdown-item:contains('Attach Files')",
            async run() {
                const extratxt = new File(["hello 2"], "extra.txt", { type: "text/plain" });
                await inputFiles(".o-mail-Message .o_input_file", [extratxt]);
            },
        },
        {
            trigger: ".o-mail-Message .o-mail-Composer .o-mail-AttachmentCard:not(.o-isUploading)", // waiting the attachment to be uploaded
        },
        {
            content: "Check the earlier provided extra attachment is listed",
            trigger: '.o-mail-Message .o-mail-Composer .o-mail-AttachmentCard[title="extra.txt"]',
        },
        {
            content: "Save edited message",
            trigger: ".o-mail-Message a:contains(save)",
            run: "click",
        },
        {
            content: "Check message is edited",
            trigger: '.o-mail-Message-body:contains("vegetables")',
        },
        {
            content: "Check edited message contains the first attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentCard:contains("text.txt")',
        },
        {
            content: "Check edited message contains the extra attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentCard:contains("extra.txt")',
            async run() {
                await click(".o-mail-AttachmentCard-unlink", {
                    parent: [".o-mail-AttachmentCard", { text: "extra.txt" }],
                });
                await click(".btn", { text: "Ok", parent: [".modal", { text: "Confirmation" }] });
                await contains(".o-mail-AttachmentCard", { text: "extra.txt", count: 0 });
            },
        },
        {
            content: "Open search panel",
            trigger: "button[title='Search Messages']",
            run: "click",
        },
        {
            content: "Search for the attachment name",
            trigger: ".o_searchview_input",
            run: "edit text.txt",
        },
        {
            content: "Trigger the search",
            trigger: "button[aria-label='Search button']",
            run: "click",
        },
        {
            content: "Check that searched message contains the attachment",
            trigger:
                '.o-mail-SearchMessagesPanel .o-mail-Message .o-mail-AttachmentCard:contains("text.txt")',
        },
    ],
});
