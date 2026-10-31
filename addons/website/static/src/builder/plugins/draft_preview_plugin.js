import { Plugin } from "@html_editor/plugin";
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
    };
}

registry.category("website-plugins").add(DraftPreviewPlugin.id, DraftPreviewPlugin);
