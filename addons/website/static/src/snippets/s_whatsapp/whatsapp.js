import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export class Whatsapp extends Interaction {
    static selector = ".s_whatsapp";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        fab: () => this.el.querySelector("#wa-fab"),
        sendBtn: () => this.el.querySelector(".wa-send"),
        ctaBtn: () => this.el.querySelector(".cta-btn"),
        closeBtn: () => this.el.querySelector(".close-btn"),
    };
    dynamicContent = {
        fab: { "t-on-click": this.toggleChat },
        sendBtn: { "t-on-click": this.sendMessage },
        ctaBtn: { "t-on-click": this.sendMessage },
        closeBtn: { "t-on-click": this.closeChat },
    };

    setup() {
        this.chatbox = this.el.querySelector(".chatbox");
        this.input = this.el.querySelector(".wa-user-message");
    }

    async willStart() {
        if(this.el.dataset.whatsappNumber || !user.userId) {
            return;
        }
        const websiteId = this.env.services.website_page.context.website_id;
        const companyId = await this.env.services.orm
            .call("website", "read", [[websiteId], ["company_id"]])
            .then((res) => res[0].company_id[0]);
        const company = await this.env.services.orm.searchRead(
            "res.company",
            [["id", "=", companyId]],
            ["phone"]
        );
        this.companyNumber = company[0]?.phone || "";
    }

    start() {
        // If no WhatsApp number is configured, we set the company phone number
        // as default WhatsApp number.
        if (!this.el.dataset.whatsappNumber && this.companyNumber) {
            this.el.dataset.whatsappNumber = this.companyNumber.replace(/\D/g, "");
        }
    }

    toggleChat() {
        this.chatbox.classList.toggle("d-none");
    }

    closeChat() {
        this.chatbox.classList.add("d-none");
    }

    sendMessage() {
        const userMessage = this.input.value.trim() || "";
        const companyNumber = this.el.dataset.whatsappNumber;
        // clean the number to keep only digits
        if (!companyNumber) {
            console.warn("WhatsApp number is not configured.");
            return;
        }
        const cleanCompanyNumber = companyNumber.replace(/\D/g, "");
        const url = `https://wa.me/${cleanCompanyNumber}?text=${encodeURIComponent(userMessage)}`;
        window.open(url, "_blank");
    }
}

registry.category("public.interactions").add("website.whatsapp", Whatsapp);
registry.category("public.interactions.edit").add("website.whatsapp", {
    Interaction: Whatsapp,
});
