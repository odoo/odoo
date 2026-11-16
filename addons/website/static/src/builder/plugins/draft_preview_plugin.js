import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const LIVE_OPTION_TEMPLATES = [
    "website.TopMenuVisibilityOption",
    "website.BreadcrumbVisibilityOption",
    "website.HideFooterOption",
    "website.CoverPropertiesOption",
    "website.ControllerPageListingLayoutOption",
];

export class DraftPreviewPlugin extends Plugin {
    static id = "draftPreview";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        option_disabled_reason_providers: (Option, el) => {
            if (
                this.services.website.isDraftPreview &&
                (LIVE_OPTION_TEMPLATES.includes(Option.template) ||
                    (Option.template === "website.SearchbarOption" &&
                        el.matches(".o_header_searchbar")))
            ) {
                return _t("These settings are saved on the live website, they can't be changed in draft mode.");
            }
        },
        on_will_setup_editor_handlers: () => {
            for (const el of selectElements(this.editable, "[data-oe-readonly=draft]")) {
                if (!el.hasAttribute("title")) {
                    el.title = _t(
                        "This content is saved on the live website, it can only be changed from the backend."
                    );
                    el.dataset.draftLiveField = "";
                }
            }
        },
        clean_for_save_processors: (root) => {
            for (const el of selectElements(root, "[data-draft-live-field]")) {
                el.removeAttribute("title");
                delete el.dataset.draftLiveField;
            }
            return root;
        },
    };
}

registry.category("website-plugins").add(DraftPreviewPlugin.id, DraftPreviewPlugin);
