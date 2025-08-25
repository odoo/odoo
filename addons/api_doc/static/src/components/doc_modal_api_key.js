import { Component, useExternalListener, useRef } from "@odoo/owl";

export class ApiKeyModal extends Component {
    static template = "web.DocApiKeyModal";

    static components = {};
    static props = {};

    setup() {
        this.modalRef = useRef("modalRef");

        useExternalListener(window, "keydown", (event) => {
            if (event.key === "Escape") {
                this.cancel();
            }
        });

        useExternalListener(window, "click", (event) => {
            if (!this.modalRef.el.contains(event.target)) {
                this.cancel();
            }
        });
    }

    save() {
        this.env.modelStore.setAPIKey(this.modalRef.el.querySelector(":scope input").value.trim());
        this.env.modelStore.showApiKeyModal = false;
    }

    cancel() {
        this.env.modelStore.showApiKeyModal = false;
    }

    async openAPIKeyForm() {
        window.open(`${window.location.origin}/odoo/action-doc_api_key_wizard`, "_blank");
    }
}
