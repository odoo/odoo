import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BEGIN } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class WhatsappOption extends BaseOptionComponent {
    static template = "website.WhatsappOption";
    static selector = ".s_whatsapp";
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            whatsappNumber: editingElement.dataset.whatsappNumber,
        }));
    }
}

class WhatsappOptionPlugin extends Plugin {
    static id = "whatsappOption";
    resources = {
        builder_options: [withSequence(BEGIN, WhatsappOption)],
        builder_actions: {
            ToggleChatBoxAction,
            AgentNameAction,
            AgentDescriptionAction,
            DefaultMessageAction,
            WhatsappNumberAction,
        },
        remove_overlay_options: (el) => el.matches(".s_whatsapp"),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
        replace_media_dialog_params_handlers: this.applyImagesMediaDialogParams.bind(this),
        on_replaced_media_handlers: ({ newMediaEl }) => {
            // Ensure the chatbox is visible when we replace media.
            if (
                newMediaEl?.nodeType === Node.ELEMENT_NODE &&
                newMediaEl.matches(".s_whatsapp .wa-agent-img")
            ) {
                newMediaEl
                    .closest(".s_whatsapp")
                    ?.querySelector(".chatbox")
                    ?.classList.remove("d-none");
            }
        },
        content_not_editable_selectors: ".s_whatsapp",
    };
    cleanForSave({ root }) {
        root.querySelector(".s_whatsapp .chatbox")?.classList.add("d-none");
    }
    onSnippetDropped({ snippetEl }) {
        // Open chatbox when whatsapp snippet is dropped.
        snippetEl.querySelector(".chatbox")?.classList.remove("d-none");
    }
    applyImagesMediaDialogParams(params) {
        if (
            params.node?.nodeType === Node.ELEMENT_NODE &&
            params.node.matches(".s_whatsapp .wa-agent-img")
        ) {
            params.visibleTabs = ["IMAGES"];
        }
    }
}

export class ToggleChatBoxAction extends BuilderAction {
    static id = "toggleChatBox";
    apply({ editingElement }) {
        // Ensure the chatbox is visible when changing the chatbox elements.
        editingElement.querySelector(".s_whatsapp .chatbox")?.classList.remove("d-none");
    }
}

export class AgentNameAction extends BuilderAction {
    static id = "agentName";
    static dependencies = ["builderActions"];
    apply({ editingElement, value }) {
        editingElement.querySelector(".wa-agent-name").textContent = value;
        this.dependencies.builderActions.getAction("toggleChatBox").apply({
            editingElement: editingElement,
        });
    }
}

export class AgentDescriptionAction extends BuilderAction {
    static id = "agentDescription";
    static dependencies = ["builderActions"];
    apply({ editingElement, value }) {
        editingElement.querySelector(".wa-agent-description").textContent = value;
        this.dependencies.builderActions.getAction("toggleChatBox").apply({
            editingElement: editingElement,
        });
    }
}

export class DefaultMessageAction extends BuilderAction {
    static id = "defaultMessage";
    static dependencies = ["builderActions"];
    apply({ editingElement, value }) {
        editingElement.querySelector(".wa-agent-msg").textContent = value;
        this.dependencies.builderActions.getAction("toggleChatBox").apply({
            editingElement: editingElement,
        });
    }
}

export class WhatsappNumberAction extends BuilderAction {
    static id = "whatsappNumber";
    getValue({ editingElement }) {
        return editingElement.dataset.whatsappNumber;
    }
    apply({ editingElement, value }) {
        if (value) {
            editingElement.dataset.whatsappNumber = value;
        }
    }
}

registry.category("website-plugins").add(WhatsappOptionPlugin.id, WhatsappOptionPlugin);
