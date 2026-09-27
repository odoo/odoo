import { registry } from "@web/core/registry";
import { Whatsapp } from "./whatsapp.js";

export const WhatsappEdit = (I) =>
    class extends I {
        getConfigurationSnapshot() {
            let snapshot = super.getConfigurationSnapshot();
            snapshot = JSON.parse(snapshot || "{}");
            snapshot.agentName = this.getTranslatableValue("agent_name");
            snapshot.agentDescription = this.getTranslatableValue("agent_description");
            snapshot.agentMessage = this.getTranslatableValue("agent_message");
            snapshot.agentAvatarSrc = this.el.dataset.agentAvatarSrc;
            return JSON.stringify(snapshot);
        }

        isImpactedBy(el) {
            // Trigger refresh when translation inputs change since they are
            // the source of truth but not stored in dataset
            return this.el.contains(el) && el.matches(".s_whatsapp_translation_inputs *");
        }

        start() {
            super.start();
            const shouldShow = this.el.dataset.shouldShowChatbox === "true";
            this.mountChatbox({ show: shouldShow });
            this.registerCleanup(() => {
                // We only remove the dataset when the interaction is fully
                // destroyed, not during refresh, so the open state can persist
                // across re-renders.
                if (!this.services["public.interactions"].isRefreshing) {
                    delete this.el.dataset.shouldShowChatbox;
                }
            });
        }

        toggleChat() {
            const chatbox = this.mountChatbox();
            const shouldShow = chatbox.classList.contains("d-none");
            this.el.dataset.shouldShowChatbox = String(shouldShow);
            chatbox.classList.toggle("d-none", !shouldShow);
        }
    };

registry.category("public.interactions.edit").add("website.whatsapp", {
    Interaction: Whatsapp,
    mixin: WhatsappEdit,
});
