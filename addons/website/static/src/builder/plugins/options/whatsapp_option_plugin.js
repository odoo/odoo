import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

class WhatsappOptionPlugin extends Plugin {
    static id = "whatsappOption";
    static dependencies = ["history"];
    resources = {
        builder_options: [
            {
                template: "website.WhatsappOption",
                selector: ".s_whatsapp",
            },
        ],
        builder_actions: {
            AgentNameAction,
            AgentDescriptionAction,
            WhatsappNumberAction,
            DefaultMessageAction,
        },
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    cleanForSave({ root }) {
        root.querySelector(".s_whatsapp_container .chatbox")?.classList.add("d-none");
    }
}

export class AgentNameAction extends BuilderAction {
    static id = "agentName";
    static dependencies = ["whatsappOption"];
    getValue({ editingElement }) {
        return editingElement.dataset["agentName"];
    }
    apply({ editingElement, value }) {
        editingElement.querySelector(".agent-name").textContent = value;
        editingElement.dataset["agentName"] = value;
    }
}

export class AgentDescriptionAction extends BuilderAction {
    static id = "agentDescription";
    static dependencies = ["whatsappOption"];
    getValue({ editingElement }) {
        return editingElement.dataset["agentDescription"];
    }
    apply({ editingElement, value }) {
        editingElement.querySelector(".agent-description").textContent = value;
        editingElement.dataset["agentDescription"] = value;
    }
}

export class WhatsappNumberAction extends BuilderAction {
    static id = "whatsappNumber";
    static dependencies = ["whatsappOption"];
    getValue({ editingElement }) {
        return editingElement.dataset["whatsappNumber"];
    }
    apply({ editingElement, value }) {
        editingElement.dataset["whatsappNumber"] = value;
    }
}

export class DefaultMessageAction extends BuilderAction {
    static id = "defaultMessage";
    static dependencies = ["whatsappOption"];
    getValue({ editingElement }) {
        return editingElement.dataset["defaultMessage"];
    }
    apply({ editingElement, value }) {
        editingElement.querySelector(".agent-msg").textContent = value;
        editingElement.dataset["defaultMessage"] = value;
    }
}

registry.category("website-plugins").add(WhatsappOptionPlugin.id, WhatsappOptionPlugin);
