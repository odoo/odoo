import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { Interaction } from "@web/public/interaction";

export class Whatsapp extends Interaction {
    static selector = ".s_whatsapp";
    dynamicContent = {
        ".wa-fab, .wa-close-btn": { "t-on-click": this.toggleChat },
        ".wa-send, .wa-cta-btn": { "t-on-click": this.sendMessage },
        ".wa-user-message": {
            "t-on-keydown": this.onKeydownMessage,
            "t-on-input": this.autoGrow,
        },
    };

    start() {
        this.chatbox = this.el.querySelector(".chatbox");
        const rawNumber = this.el.dataset.whatsappNumber || "";
        this.companyNumber = rawNumber.replace(/[^\d]/g, "");
    }

    getTranslatableValue(name) {
        const inputEl = this.el.querySelector(
            `.s_whatsapp_translation_inputs input[name="${name}"]`
        );
        return inputEl?.getAttribute("value") || "";
    }

    getChatboxData() {
        return {
            agentName: this.getTranslatableValue("agent_name"),
            agentDescription: this.getTranslatableValue("agent_description"),
            agentMessage: this.getTranslatableValue("agent_message"),
            agentAvatarSrc: this.el.dataset.agentAvatarSrc,
            messagePlaceholder: this.getTranslatableValue("message_placeholder"),
            ctaLabel: this.getTranslatableValue("cta_label"),
        };
    }

    mountChatbox({ show = false } = {}) {
        if (!this.chatbox) {
            [this.chatbox] = this.renderAt(
                "website.s_whatsapp.chatbox",
                this.getChatboxData(),
                this.el
            );
            this.updateAvailabilityState();
        }
        if (show) {
            this.chatbox.classList.remove("d-none");
        }
        return this.chatbox;
    }

    updateAvailabilityState() {
        if (!this.chatbox) {
            return;
        }
        const hasNumber = !!this.companyNumber;
        const warningEl = this.chatbox.querySelector(".wa-warning");
        const userInputEl = this.chatbox.querySelector(".wa-user-input");
        // Show warning if no WhatsApp number is configured
        warningEl?.classList.toggle("d-none", hasNumber);
        userInputEl?.classList.toggle("d-none", !hasNumber);
    }

    toggleChat() {
        // If chatbox is not mounted, create and append it
        if (!this.chatbox) {
            this.mountChatbox({ show: true });
            return;
        }
        // Otherwise, remove it (toggle behavior)
        this.chatbox.remove();
        this.chatbox = null;
    }

    sendMessage() {
        const inputEl = this.chatbox.querySelector(".wa-user-message");
        const messageText = inputEl.value.trim() || "";
        const whatsappUrl = `https://wa.me/${this.companyNumber}?text=${encodeURIComponent(
            messageText
        )}`;
        browser.open(whatsappUrl, "_blank");
    }

    onKeydownMessage(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    autoGrow(ev) {
        const textAreaEl = ev.target;
        textAreaEl.style.height = "auto";
        textAreaEl.style.height = `${textAreaEl.scrollHeight}px`;
    }
}

registry.category("public.interactions").add("website.whatsapp", Whatsapp);
