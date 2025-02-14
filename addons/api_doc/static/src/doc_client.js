import { Component, useState, xml, onMounted, useSubEnv } from "@odoo/owl";
import { ModelStore } from "@api_doc/doc_model_store";
import { useDocUI } from "@api_doc/utils/doc_ui_store";
import { ApiKeyModal } from "@api_doc/components/doc_modal_api_key";
import { SearchModal } from "@api_doc/components/doc_modal_search";
import { DocSidebar } from "@api_doc/components/doc_sidebar";
import { DocModel } from "@api_doc/components/doc_model";

export class DocClient extends Component {
    static template = xml`
        <header class="position-fixed bg-1 flex gap-1 align-items-center justify-content-between w-100">
            <div class="flex">
                <h2>Odoo Runtime Doc</h2>
            </div>
            <div>
                <input
                    t-on-click="() => this.state.showSearchModal = true"
                    placeholder="Find anything..."
                />
            </div>
            <div class="flex gap-1">
                <button class="btn" role="button" t-on-click="() => this.env.modelStore.showApiKeyModal = true">
                    <i class="fa fa-key" aria-hidden="true"></i>
                </button>
                <button class="btn" role="button" t-on-click="() => this.toggleTheme()">
                    <i class="fa fa-moon-o" aria-hidden="true"></i>
                </button>
            </div>
        </header>
        <main class="position-relative flex">
            <DocSidebar t-if="!ui.isSmall"/>
            <t t-if="modelStore.models.length > 0">
                <DocModel t-if="modelStore.activeModel"/>
            </t>
            <div t-elif="!modelStore.error" class="h-100 w-100 flex align-items-center justify-content-center gap-1">
                <i class="fa fa-spinner o-doc-spinner" aria-hidden="true"></i>
                <div>Loading Models</div>
            </div>

            <div t-if="modelStore.error" class="flex align-items-center justify-content-center w-100 h-100">
                <div class="alert error mt-1 flex flex-column">
                    <h5 class="mb-2 flex align-items-center">
                        <i class="pe-1 fa fa-exclamation-triangle" aria-hidden="true"></i>
                        <span>Error while loading models</span>
                    </h5>
                    <div t-out="modelStore.error.message"></div>
                </div>
            </div>
        </main>
        <ApiKeyModal t-if="modelStore.showApiKeyModal"/>
        <SearchModal
            t-if="state.showSearchModal"
            close="() => this.state.showSearchModal = false"
        />
    `;

    static components = {
        DocSidebar,
        DocModel,
        ApiKeyModal,
        SearchModal,
    };t
    static props = {};

    setup() {
        this.setTheme(localStorage.getItem("theme") || "odoo-dark");

        this.ui = useDocUI();
        this.modelStore = useState(new ModelStore());
        useSubEnv({ modelStore: this.modelStore });

        this.state = useState({ showSearchModal: false });

        onMounted(async () => {
            await this.modelStore.loadModels();
            this.selectUrlModel();
        });

        window.addEventListener("popstate", () => {
            this.selectUrlModel();
        });
    }

    selectUrlModel() {
        const actives = {};
        const parts = window.location.pathname.split("/");
        const docIndex = parts.indexOf("doc");
        const urlModel = parts[docIndex + 1];
        if (urlModel) {
            const model = this.modelStore.getBasicModelData(urlModel);
            if (model) {
                actives.model = model;
            }
        }

        const hash = window.location.hash.substring(1);
        const model = actives.model;
        if (model && hash) {
            if (model.methods.includes(hash)) {
                actives.method = hash;
            } else if (model.fields[hash]) {
                actives.field = hash;
            }
        }

        this.modelStore.setActiveModel(actives);
    }

    toggleTheme() {
        this.setTheme(this.theme === "odoo-dark" ? "odoo-light" : "odoo-dark");
    }

    setTheme(theme) {
        this.theme = theme;
        localStorage.setItem("theme", theme);
        document.body.setAttribute("theme", theme);
    }
}
