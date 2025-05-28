import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { generateGMapLink } from "@website/js/utils";

class MapOptionPlugin extends Plugin {
    static id = "mapOption";
    resources = {
        builder_options: [
            {
                template: "website.mapOption",
                selector: ".s_map",
            },
        ],
        so_content_addition_selector: [".s_map"],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            mapUpdateSrc: {
                apply: ({ editingElement }) => {
                    const embedded = editingElement.querySelector(".s_map_embedded");

                    if (editingElement.dataset.mapAddress) {
                        const url = generateGMapLink(editingElement.dataset);
                        if (url !== embedded.getAttribute("src")) {
                            embedded.setAttribute("src", url);
                        }
                    } else {
                        embedded.setAttribute("src", "about:blank");
                    }
                    embedded.classList.toggle("d-none", !editingElement.dataset.mapAddress);
                    editingElement
                        .querySelector(".missing_option_warning")
                        .classList.toggle("d-none", !!editingElement.dataset.mapAddress);
                },
            },
            mapDescription: {
                isApplied: ({ editingElement }) =>
                    editingElement.querySelector(".description") !== null,
                apply: ({ editingElement }) => {
                    editingElement.appendChild(
                        document.createRange().createContextualFragment(
                            `<div class="description">
                                <strong>${_t("Visit us:")}</strong>
                                ${_t("Our office is open Monday – Friday 8:30 a.m. – 4:00 p.m.")}
                            </div>`
                        )
                    );
                },
                clean: ({ editingElement }) => {
                    editingElement.querySelector(".description").remove();
                },
            },
        };
    }
}

registry.category("website-plugins").add(MapOptionPlugin.id, MapOptionPlugin);
