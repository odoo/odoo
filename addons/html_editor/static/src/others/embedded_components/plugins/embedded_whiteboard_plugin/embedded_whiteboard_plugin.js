import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { withSequence } from "@html_editor/utils/resource";
import { WhiteboardPopover } from "./whiteboard_popover";

export class EmbeddedWhiteboardPlugin extends Plugin {
    static id = "embeddedWhiteboard";
    static dependencies = ["dom", "history", "link", "overlay", "powerbox", "selection"];
    static shared = [];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "embedWhiteboard",
                title: _t("Embed whiteboard"),
                description: _t("Embed a whiteboard or a diagram"),
                iconClass: "o_embed_whiteboard_icon",
                run: this.openEmbedPopup.bind(this),
                isAvailable: () => this.config.allowWhiteboard,
            },
        ],
        powerbox_categories: withSequence(60, { id: "whiteboard", name: _t("Whiteboard") }),
        powerbox_items: [
            {
                categoryId: "whiteboard",
                commandId: "embedWhiteboard",
            },
        ],
        paste_url_overrides: this.openPowerboxOnUrlPaste.bind(this),
        whiteboard_embedded_props_providers: [
            // Miro
            (url) => {
                const miroRegex =
                    /^https:\/\/miro\.com\/app\/board\/(?<boardId>[^/?]+)\/?\?(.*&)*share_link_id=(?<embedId>[^&]+)(?:&|$)/;
                const miroMatch = miroRegex.exec(url);
                if (miroMatch) {
                    const previewUrl = `https://miro.com/app/live-embed/${miroMatch.groups.boardId}/?embedMode=view_only_without_ui&embedId=${miroMatch.groups.embedId}`;
                    return {
                        type: "miro",
                        previewUrl,
                        error: false,
                    };
                } else if (url.startsWith("https://miro.com/app/live-embed/")) {
                    return {
                        type: "miro",
                        previewUrl: url,
                        error: false,
                    };
                }
            },
            // Google Docs
            (url) => {
                if (url.startsWith("https://docs.google.com/")) {
                    return {
                        type: "google",
                        previewUrl: url
                            .replace("/edit?", "/preview?")
                            .replace("/edit", "/preview")
                            .replace("/view?", "/preview?")
                            .replace("/view", "/preview"),
                        url: url
                            .replace("/preview?", "/edit?")
                            .replace("/preview", "/edit")
                            .replace("/view?", "/edit?")
                            .replace("/view", "/edit"),
                        error: false,
                    };
                }
            },
            // Figma
            (url) => {
                if (/^https:\/\/[^/]*figma\.com\//.exec(url)) {
                    const parsedUrl = new URL(url);
                    const nodeId = parsedUrl.searchParams.get("node-id");
                    parsedUrl.hostname = "www.figma.com";
                    parsedUrl.search = "";
                    parsedUrl.searchParams.set("node-id", nodeId);
                    parsedUrl.searchParams.set("p", "f");
                    url = parsedUrl.toString();
                    parsedUrl.hostname = "embed.figma.com";
                    parsedUrl.search = "";
                    parsedUrl.searchParams.set("node-id", nodeId);
                    parsedUrl.searchParams.set("embed-host", "share");
                    const previewUrl = parsedUrl.toString();
                    return {
                        type: "figma",
                        url,
                        previewUrl,
                        error: false,
                    };
                }
            },
            // Canva
            (url) => {
                if (url.startsWith("https://www.canva.com/")) {
                    const parsedUrl = new URL(url);
                    if (parsedUrl.pathname.endsWith("/edit")) {
                        parsedUrl.pathname = parsedUrl.pathname.replace("/edit", "/view");
                    }
                    parsedUrl.search = "";
                    const previewUrl = parsedUrl.toString();
                    parsedUrl.search = "embed";
                    const embedUrl = parsedUrl.toString();
                    return {
                        type: "canva",
                        error: false,
                        previewUrl,
                        embedUrl,
                    };
                }
            },
        ],
    };

    setup() {
        this.overlay = this.dependencies.overlay.createOverlay(WhiteboardPopover, {
            hasAutofocus: true,
            className: "popover",
        });
    }

    /**
     * @param {string} text
     * @param {string} url
     */
    openPowerboxOnUrlPaste(text, url) {
        if (!url || !this.config.allowWhiteboard) {
            return;
        }
        const providerProps = this.getResource("whiteboard_embedded_props_providers")
            .map((provider) => provider(url))
            .filter(Boolean);
        if (providerProps.length && !providerProps[0].error) {
            const commands = [
                {
                    title: _t("Embed as whiteboard"),
                    description: _t("Embed as a whiteboard or as a diagram"),
                    iconClass: "o_embed_whiteboard_icon",
                    run: () => this.insertWhiteboardElement({ url, ...providerProps[0] }),
                },
                this.dependencies.link.getPathAsUrlCommand(text, url),
            ];
            const restoreSavepoint = this.dependencies.history.makeSavePoint();
            // Open powerbox with commands to embed whiteboard or paste as link.
            // Insert URL as text, revert it later if a command is triggered.
            this.dependencies.dom.insert(text);
            this.dependencies.history.commit();
            this.dependencies.powerbox.openPowerbox({
                commands,
                onApplyCommand: restoreSavepoint,
                onClose: () => (this.isEmbedPowerBoxVisible = false),
            });
            this.isEmbedPowerBoxVisible = true;
            return true;
        }
    }

    openEmbedPopup({ target } = {}) {
        this.overlay.open({
            props: {
                close: () => {
                    this.overlay.close();
                },
                process: (url) => {
                    if (!url) {
                        return;
                    }
                    const embeddedProps = {
                        url,
                        error: true,
                    };
                    const providerProps = this.getResource("whiteboard_embedded_props_providers")
                        .map((provider) => provider(url))
                        .filter(Boolean);
                    if (providerProps.length) {
                        Object.assign(embeddedProps, providerProps[0]);
                    } else {
                        embeddedProps.type = "unknown";
                    }
                    return embeddedProps;
                },
                apply: this.insertWhiteboardElement.bind(this),
            },
            target,
        });
    }

    insertWhiteboardElement(embeddedProps) {
        const embedEl = renderToElement("html_editor.WhiteboardBlueprint", {
            embeddedProps: JSON.stringify(embeddedProps),
        });
        this.dependencies.dom.insert(embedEl);
        this.dependencies.history.commit();
        this.dependencies.selection.setSelection({
            anchorNode: embedEl.parentElement,
            anchorOffset: [...embedEl.parentElement.children].indexOf(embedEl) + 1,
        });
    }
}
