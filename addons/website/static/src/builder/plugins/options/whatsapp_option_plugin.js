import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BuilderAction } from "@html_builder/core/builder_action";
import { useDomState } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ShowOnOption } from "../floating_snippets_plugin";

export class WhatsappOption extends BaseOptionComponent {
    static id = "whatsapp_option";
    static template = "website.WhatsappOption";
    static components = { ShowOnOption };
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            whatsappNumber: editingElement.dataset.whatsappNumber,
        }));
    }
}

class WhatsappOptionPlugin extends Plugin {
    static id = "whatsappOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            ShowChatBoxAction,
            ReplaceAgentAvatarAction,
            WhatsappNumberAction,
        },
        floating_snippets_selectors: ".s_whatsapp",
        system_attributes: ["data-should-show-chatbox"],
        should_remove_overlay_options_predicates: (el) => {
            if (el.matches(".s_whatsapp")) {
                return true;
            }
        },
        is_valid_for_sibling_dropzone_predicates: (el) => {
            if (el.closest(".s_whatsapp")) {
                return false;
            }
        },
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            // Chatbox is rendered by the interaction, so we use a 'temporary'
            // flag to make it open by default on initialization.
            if (snippetEl.matches(".s_whatsapp")) {
                snippetEl.dataset.shouldShowChatbox = "true";
            }
        },
    };
}

export class ShowChatBoxAction extends BuilderAction {
    static id = "showChatBox";

    apply({ editingElement }) {
        const rootWhatsappEl = editingElement.closest(".s_whatsapp");
        if (rootWhatsappEl) {
            rootWhatsappEl.dataset.shouldShowChatbox = "true";
        }
    }
}

export class ReplaceAgentAvatarAction extends ShowChatBoxAction {
    static id = "replaceAgentAvatar";
    static dependencies = ["media"];

    setup() {
        super.setup();
        this.preview = false;
        this.canTimeout = false;
    }

    async apply({ editingElement }) {
        // The avatar is created dynamically and gets re-rendered by interaction
        // so the element may not exist when the builder tries to target it.
        // That’s why we didn’t use the standard replaceMedia action.
        await this.dependencies.media.openMediaDialog({
            onlyImages: true,
            save: (newMediaEl) => {
                const src = newMediaEl.getAttribute("src");
                if (src) {
                    editingElement.dataset.agentAvatarSrc = src;
                    super.apply({ editingElement });
                }
            },
        });
    }
}

export class WhatsappNumberAction extends ShowChatBoxAction {
    static id = "whatsappNumber";

    getValue({ editingElement }) {
        return editingElement.dataset.whatsappNumber;
    }

    apply({ editingElement, value }) {
        // Prevent clearing: only update if a non-empty value is provided
        if (value) {
            // A WhatsApp number is now configured, so hide warning and enable
            // the chatbox input for user interaction.
            const warningEl = editingElement.querySelector(".s_whatsapp_warning");
            const userInputEl = editingElement.querySelector(".s_whatsapp_user_input");
            warningEl?.classList.add("d-none");
            userInputEl?.classList.remove("d-none");
            editingElement.dataset.whatsappNumber = value;
            super.apply({ editingElement });
        }
    }
}

registry.category("website-options").add(WhatsappOption.id, WhatsappOption);
registry.category("website-plugins").add(WhatsappOptionPlugin.id, WhatsappOptionPlugin);
