import { Component, xml, useExternalListener, useRef } from "@odoo/owl";
import { useModelStore } from "@web/doc/utils/doc_model_store";

export class ApiKeyModal extends Component {
    static template = xml`
        <div class="modal-bg flex justify-content-center align-items-center">
            <div class="modal p-2 flex flex-column mb-1" t-ref="modalRef">
                <h2 class="mb-2">API key</h2>

                <p>To try the API, please insert your API key here</p>
                <input
                    class="mt-1"
                    type="text"
                    autocorrect="off"
                    t-att-value="store.apiKey"
                    t-on-input="onInput"
                />

                <div class="flex flex-content-between mt-3">
                    <button class="btn me-1" t-on-click="save">Save</button>
                    <button class="btn" t-on-click="cancel">Cancel</button>
                </div>
            </div>
        </div>
    `;

    static components = {};
    static props = {};

    setup() {
        this.modalRef = useRef("modalRef");
        this.store = useModelStore();
        this.value = null;

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

    onInput(event) {
        this.value = event.target.value.trim();
    }

    save() {
        this.store.setAPIKey(this.value);
        this.store.showApiKeyModal = false;
    }

    cancel() {
        this.store.showApiKeyModal = false;
    }
}
