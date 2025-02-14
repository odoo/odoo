import { Component, useState, xml, onMounted } from "@odoo/owl";
import { ApiKeyModal } from "@web/doc/components/doc_model_api_key";
import { SearchModal } from "@web/doc/components/doc_modal_search";
import { DocSidebar } from "@web/doc/components/doc_sidebar";
import { DocModel } from "@web/doc/components/doc_model";
import { useModelStore } from "@web/doc/utils/doc_model_store";

export class DocClient extends Component {
    static template = xml`
        <header class="position-fixed bg-1 flex align-items-center justify-content-between w-100">
            <div class="flex">
                <h2>Odoo Runtime Doc</h2>
            </div>
            <div>
                <input
                    style="min-width: 15rem"
                    t-on-click="() => this.state.showSearchModal = true"
                    placeholder="Find anything..."
                />
            </div>
            <div class="flex">
                <button class="btn me-2" role="button" t-on-click="() => this.modelStore.showApiKeyModal = true">
                    <i class="fa fa-cog" aria-hidden="true"></i>
                </button>
                <button class="btn" role="button" t-on-click="() => this.toggleTheme()">
                    <i class="fa fa-moon-o" aria-hidden="true"></i>
                </button>
            </div>
        </header>
        <main>
            <DocSidebar
                activeModel="this.state.model"
                onModelSelected="model => this.onModelSelected(model)"
            />
            <t t-if="modelStore.models.length > 0">
                <DocModel t-if="state.model" modelId="state.model.model"/>
            </t>
            <div t-else="" class="h-100 w-100 flex align-items-center justify-content-center gap-1">
                <i class="fa fa-spinner o-doc-spinner" aria-hidden="true"></i>
                <div>Loading Models</div>
            </div>
        </main>
        <ApiKeyModal t-if="modelStore.showApiKeyModal"/>
        <SearchModal
            t-if="state.showSearchModal"
            close="() => this.state.showSearchModal = false"
            onSelect="(result) => this.selectSearchResult(result)"
        />
    `;

    static components = {
        DocSidebar,
        DocModel,
        ApiKeyModal,
        SearchModal,
    };
    static props = {};

    setup() {
        this.setTheme(localStorage.getItem("theme") || "odoo-dark");
        this.modelStore = useModelStore();

        this.state = useState({
            model: undefined,
            showSearchModal: false,
        });

        onMounted(async () => {
            await this.modelStore.loadModels();
            this.selectUrlModel();
        });

        window.addEventListener("popstate", () => {
            this.selectUrlModel();
        });
    }

    selectUrlModel() {
        const parts = window.location.pathname.split("/");
        const docIndex = parts.indexOf("doc");
        const urlModel = parts[docIndex + 1];

        if (urlModel) {
            for (const addon of this.modelStore.addons) {
                for (const model of addon.models) {
                    if (model.model === urlModel) {
                        this.state.model = model;
                        return;
                    }
                }
            }
        }
    }

    selectSearchResult(result) {
        this.state.model = result.model;
    }

    onModelSelected(model) {
        this.state.model = model;
        window.history.pushState({}, "", `/doc/${model.model}`);
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
