import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { withSequence } from "@html_editor/utils/resource";
import { WhiteboardPopover } from "./whiteboard_popover";

export class EmbeddedWhiteboardPlugin extends Plugin {
    static id = "embeddedWhiteboard";
    static dependencies = ["dom", "history", "overlay"];
    static shared = [];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "embedWhiteboard",
                title: _t("Embed whiteboard"),
                description: _t("Embed a whiteboard or a diagram"),
                icon: "o_embed_whiteboard_icon",
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
    };

    setup() {
        this.overlay = this.dependencies.overlay.createOverlay(WhiteboardPopover, {
            hasAutofocus: true,
            className: "popover",
        });
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
                    // TODO identify provider through resource
                    const miroRegex =
                        /^https:\/\/miro\.com\/app\/board\/(?<boardId>[^/?]+)\/?\?(.*&)*share_link_id=(?<embedId>[^&]+)(?:&|$)/;
                    const miroMatch = miroRegex.exec(url);
                    if (miroMatch) {
                        const previewUrl = `https://miro.com/app/live-embed/${miroMatch.groups.boardId}/?embedMode=view_only_without_ui&embedId=${miroMatch.groups.embedId}`;
                        Object.assign(embeddedProps, {
                            type: "miro",
                            previewUrl,
                            error: false,
                        });
                    } else if (url.startsWith("https://miro.com/app/live-embed/")) {
                        Object.assign(embeddedProps, {
                            type: "miro",
                            previewUrl: url,
                            error: false,
                        });
                    } else if (url.startsWith("https://docs.google.com/")) {
                        Object.assign(embeddedProps, {
                            type: "google",
                            previewUrl: url.replace("/edit?", "/preview?"),
                            url: url.replace("/preview?", "/edit?"),
                            error: false,
                        });
                    } else if (/^https:\/\/[^/]*figma\.com\//.exec(url)) {
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
                        Object.assign(embeddedProps, {
                            type: "figma",
                            url,
                            previewUrl,
                            error: false,
                        });
                    } else if (url.startsWith("https://www.canva.com/")) {
                        const parsedUrl = new URL(url);
                        if (parsedUrl.pathname.endsWith("/edit")) {
                            parsedUrl.pathname = parsedUrl.pathname.replace("/edit", "/view");
                        }
                        parsedUrl.search = "";
                        const previewUrl = parsedUrl.toString();
                        parsedUrl.search = "embed";
                        const embedUrl = parsedUrl.toString();
                        Object.assign(embeddedProps, {
                            type: "canva",
                            error: false,
                            previewUrl,
                            embedUrl,
                        });
                    } else {
                        embeddedProps.type = "unknown";
                    }
                    return embeddedProps;
                },
                apply: (embeddedProps) => {
                    const embedEl = renderToElement("html_editor.WhiteboardBlueprint", {
                        embeddedProps: JSON.stringify(embeddedProps),
                    });
                    this.dependencies.dom.insert(embedEl);
                    this.dependencies.history.commit();
                },
            },
            target,
        });
    }
}
