import { reactive } from "@odoo/owl";
import { waitFor } from "@odoo/hoot-dom";

import { registry } from "@web/core/registry";
import { getOrigin } from "@web/core/utils/urls";
import { click, inputFiles } from "@web/../tests/utils";

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
            trigger: ".o_discuss_channel_public_modules_loaded",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "edit cheese",
        },
        { trigger: ".o-mail-Composer button[title='More Actions']", run: "click" },
        {
            trigger: ".dropdown-item:contains('Attach Files')",
            async run() {
                const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
                await inputFiles(".o-mail-Composer .o_input_file", [text]);
            },
        },
        {
            trigger: ".o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt)",
        },
        {
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
            trigger: '.o-mail-AttachmentContainer:not(.o-isUploading)[title="image.png"]',
            async run() {
                /** @type {import("models").Store} */
                const store = odoo.__WOWL_DEBUG__.root.env.services["mail.store"];
                if (store.self.type === "guest") {
                    const src = this.anchor.querySelector("img").src;
                    const attachment = store["ir.attachment"].get(
                        (src.match("/web/image/([0-9]+)") || []).at(-1)
                    );
                    if (!attachment) {
                        throw new Error(`Attachment was not found from src: ${src}`);
                    }
                    if (!attachment.raw_access_token) {
                        await new Promise((resolve) => {
                            const proxy = reactive(attachment, () => {
                                if (attachment.raw_access_token) {
                                    resolve();
                                } else {
                                    void proxy.raw_access_token; // keep observing until a value is received
                                }
                            });
                            void proxy.raw_access_token; // start observing
                        });
                    }
                    await waitFor(
                        `.o-mail-AttachmentContainer[title="image.png"] img[src="${getOrigin()}/web/image/${
                            attachment.id
                        }?access_token=${attachment.raw_access_token}&filename=image.png&unique=${
                            attachment.checksum
                        }"]`
                    );
                }
            },
        },
        { trigger: ".o-mail-Composer-input", run: "click" }, // focus
        {
            trigger: ".o-mail-Composer:has(button[title='Send']:enabled) .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: `${messageSelector}[data-persistent]`,
        },
        {
            trigger: `${messageSelector} .o-mail-AttachmentContainer:contains("text.txt")`,
        },
        {
            trigger: messageSelector,
            run: `hover && click ${messageSelector} [title='Add a Reaction']`,
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
            trigger: ".o-mail-Message .o-mail-Composer button[title='More Actions']",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('Attach Files')",
            async run() {
                const extratxt = new File(["hello 2"], "extra.txt", { type: "text/plain" });
                await inputFiles(".o-mail-Message .o_input_file", [extratxt]);
            },
        },
        {
            trigger:
                ".o-mail-Message .o-mail-Composer .o-mail-AttachmentContainer:not(.o-isUploading):contains(extra.txt)",
        },
        {
            trigger: ".o-mail-Message a:contains(save)",
            run: "click",
        },
        {
            trigger: editedMessageSelector,
        },
        {
            trigger: `${editedMessageSelector} .o-mail-AttachmentContainer:contains("text.txt")`,
        },
        {
            trigger: `${editedMessageSelector} .o-mail-AttachmentContainer:contains("extra.txt")`,
        },
        {
            trigger: `${editedMessageSelector} .o-mail-AttachmentContainer:contains("extra.txt") .o-mail-Attachment-unlink`,
            run: "click",
        },
        {
            trigger: ".modal:contains(Confirmation) .btn:contains(Ok)",
            run: "click",
        },
        {
            trigger: `${editedMessageSelector}:not(:has(.o-mail-AttachmentContainer:contains("extra.txt")))`,
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
            trigger: `.o-mail-SearchMessagesPanel ${editedMessageSelector} .o-mail-AttachmentContainer:contains("text.txt")`,
        },
    ],
});
