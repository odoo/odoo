import { Plugin } from "@html_editor/plugin";

/**
 * @typedef {import("@html_editor/core/user_command_plugin").UserCommand} UserCommand
 *
 * @typedef {((url: string) => UserCommand)[]} paste_media_url_command_providers
 */

export class MediaUrlPastePlugin extends Plugin {
    static id = "mediaUrlPaste";
    static dependencies = ["link", "dom", "history", "powerbox"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        paste_url_overrides: this.openPowerboxOnUrlPaste.bind(this),
    };

    /**
     * @param {string} text
     * @param {string} url
     */
    openPowerboxOnUrlPaste(text, url) {
        const commands = this.getResource("paste_media_url_command_providers")
            .map((provider) => provider(url))
            .filter(Boolean);
        if (commands.length) {
            commands.push(this.dependencies.link.getPathAsUrlCommand(text, url));
            const restoreSavepoint = this.dependencies.history.makeSavePoint();
            // Open powerbox with commands to embed media or paste as link.
            // Insert URL as text, revert it later if a command is triggered.
            this.dependencies.dom.insert(text);
            this.dependencies.history.addStep();
            this.dependencies.powerbox.openPowerbox({ commands, onApplyCommand: restoreSavepoint });
            return true;
        }
    }
}
