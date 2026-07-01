import { Component, signal, useListener } from "@odoo/owl";

export class ApiKeyModal extends Component {
    static template = "web.DocApiKeyModal";

    static components = {};
    static props = {};

    modalRef = signal(null);

    setup() {
        useListener(window, "keydown", (event) => {
            if (event.key === "Escape") {
                this.cancel();
            }
        });

        useListener(window, "click", (event) => {
            if (!this.modalRef()?.contains(event.target)) {
                this.cancel();
            }
        });
    }

    save() {
        this.env.modelStore.setAPIKey(this.modalRef()?.querySelector(":scope input")?.value.trim());
        this.env.modelStore.showApiKeyModal = false;
    }

    cancel() {
        this.env.modelStore.showApiKeyModal = false;
    }

    async openAPIKeyForm() {
        window.open(`${window.location.origin}/odoo/action-doc_api_key_wizard`, "_blank");
    }
}
