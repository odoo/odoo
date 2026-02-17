import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class Whatsapp extends Interaction {
    static selector = ".s_whatsapp";
    dynamicContent = {
        ".wa-fab": { "t-on-click": this.toggleChat },
        ".wa-send": { "t-on-click": this.sendMessage },
        ".wa-cta-btn": { "t-on-click": this.sendMessage },
        ".wa-close-btn": { "t-on-click": this.toggleChat },
        ".wa-user-message": {
            "t-on-keydown": this.onKeydownMessage,
        },
    };

    setup() {
        this.chatbox = this.el.querySelector(".chatbox");
    }

    async willStart() {
        if (!this.el.dataset.whatsappNumber) {
            this.defaultNumber = (await rpc("/website/company_phone")) || "";
        }
    }

    start() {
        // If no WhatsApp number is configured, we set the company phone number
        // as default WhatsApp number.
        const rawCompanyNumber = this.el.dataset.whatsappNumber || this.defaultNumber;
        this.companyNumber = rawCompanyNumber ? rawCompanyNumber.replace(/\D/g, "") : "";
        const hasNumber = !!this.companyNumber;
        const warningEl = this.chatbox.querySelector(".wa-warning");
        const userInputEl = this.chatbox.querySelector(".wa-user-input");
        // Show warning if no WhatsApp number is configured
        warningEl?.classList.toggle("d-none", hasNumber);
        userInputEl?.classList.toggle("d-none", !hasNumber);
        this.el.dataset.whatsappNumber = this.companyNumber;
    }

    toggleChat() {
        this.chatbox.classList.toggle("d-none");
    }

    sendMessage() {
        const inputEl = this.el.querySelector(".wa-user-message");
        const messageText = inputEl.value.trim() || "";
        const whatsappUrl = `https://wa.me/${this.companyNumber}?text=${encodeURIComponent(
            messageText
        )}`;
        window.open(whatsappUrl, "_blank");
    }

    onKeydownMessage(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }
}

registry.category("public.interactions").add("website.whatsapp", Whatsapp);
