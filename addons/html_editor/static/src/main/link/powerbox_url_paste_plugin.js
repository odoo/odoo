import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { isSingleUrl } from "./link_paste_plugin";
import { PLAIN_TEXT_MODES } from "@html_editor/core/dom_plugin";

/**
 * @typedef {import("@html_editor/core/user_command_plugin").UserCommand} UserCommand
 *
 * @typedef {((url: string) => UserCommand)[]} paste_media_url_command_providers
 */

export class MediaUrlPastePlugin extends Plugin {
    static id = "mediaUrlPaste";
    static dependencies = ["link", "dom", "history", "powerbox", "selection"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        paste_text_overrides: this.openPowerboxOnUrlPaste.bind(this),
        on_history_commit_undone_handlers: this.closePowerBox.bind(this),
    };

    /**
     * @param {string} text
     */
    openPowerboxOnUrlPaste(selection, text) {
        if (!this.dependencies.dom.shouldInsertAsPlainText(selection) && isSingleUrl(text)) {
            // Pasted content is a single URL.
            const selectionIsInsideALink = !!closestElement(selection.anchorNode, "a");
            const url = /^https?:\/\//i.test(text) ? text : "https://" + text;
            if (!selectionIsInsideALink) {
                const commands = this.getResource("paste_media_url_command_providers")
                    .map((provider) => provider(url))
                    .filter(Boolean);
                if (commands.length) {
                    commands.push(this.dependencies.link.getPathAsUrlCommand(text, url));
                    const restoreSavepoint = this.dependencies.history.makeSavePoint();
                    // Open powerbox with commands to embed media or paste as
                    // link. Insert URL as text, revert it later if a command is
                    // triggered.
                    this.dependencies.dom.insert(text, {
                        plainTextMode: PLAIN_TEXT_MODES.MULTI_LINE,
                    });
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
        }
    }

    closePowerBox() {
        if (this.isEmbedPowerBoxVisible) {
            this.dependencies.powerbox.closePowerbox();
        }
    }
}
