import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";

export class ZenPlugin extends Plugin {
    static id = "zen";
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "zen",
                title: _t("Toggle Zen mode"),
                description: _t("Helps you focus in fullscreen"),
                icon: "o_zen_icon",
                isAvailable: () => true,
                run: () => {
                    const toggle = (enable) => {
                        this.document.body.classList.toggle("o_zen_mode", enable);
                        this.editable.classList.toggle("o_zen_keep", enable);
                    };
                    const isZen = this.document.body.classList.contains("o_zen_mode");
                    if (isZen) {
                        toggle(false);
                        this.document.exitFullscreen();
                    } else {
                        this.document.body.requestFullscreen().then(() => {
                            toggle(true);
                            const listener = () => {
                                if (!this.document.fullscreenElement) {
                                    // Exiting
                                    toggle(false);
                                    this.document.body.removeEventListener(
                                        "fullscreenchange",
                                        listener
                                    );
                                }
                            };
                            this.document.body.addEventListener("fullscreenchange", listener);
                        });
                    }
                },
            },
        ],
        powerbox_categories: { id: "display_mode", name: _t("Display mode") },
        powerbox_items: [
            {
                commandId: "zen",
                categoryId: "display_mode",
            },
        ],
    };
}
