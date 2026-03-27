import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { generateGMapLink } from "@website/js/utils";

export class MapOption extends BaseOptionComponent {
    static template = "website.mapOption";
    static selector = ".s_map";
}

class MapOptionPlugin extends Plugin {
    static id = "mapOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [MapOption],
        so_content_addition_selector: [".s_map"],
        builder_actions: {
            MapUpdateSrcAction,
            MapDescriptionAction,
        },
        // TODO remove when the snippet will have a "Height" option.
        keep_overlay_options: (el) => el.matches(".s_map"),
    };
}

export class MapUpdateSrcAction extends BuilderAction {
    static id = "mapUpdateSrc";
    apply({ editingElement }) {
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
    }
}
export class MapDescriptionAction extends BuilderAction {
    static id = "mapDescription";
    isApplied({ editingElement }) {
        return editingElement.querySelector(".description") !== null;
    }
    apply({ editingElement }) {
        editingElement.appendChild(
            document.createRange().createContextualFragment(
                `<div class="description">
                    <strong>${_t("Visit us:")}</strong>
                    ${_t("Our office is open Monday – Friday 8:30 a.m. – 4:00 p.m.")}
                </div>`
            )
        );
    }
    clean({ editingElement }) {
        editingElement.querySelector(".description").remove();
    }
}

registry.category("website-plugins").add(MapOptionPlugin.id, MapOptionPlugin);
