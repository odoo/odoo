import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin, shared } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/** @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString */

/**
 * @typedef {{
 *      name: string;
 *      label: LazyTranslatedString;
 * }[]} header_icon_labels
 *
 * Label of the Header panel row replacing the icon with this
 * `data-header-icon` name. An icon without a label gets no row.
 */

const HEADER_ICON_SELECTOR = "[data-header-icon]";
const DIRTY_CLASS = "o_dirty_header_icon";

export class HeaderIconsPlugin extends Plugin {
    static id = "headerIcons";
    static dependencies = ["history", "media", "media_website", "operation"];
    static shared = shared(["replaceIcon"]);

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dirty_trackers: { selector: HEADER_ICON_SELECTOR, dirtyClass: DIRTY_CLASS, match: "self" },
        on_ready_to_save_document_handlers: this.onSave.bind(this),
        builder_actions: { ReplaceHeaderIconAction },
        header_icon_labels: [
            { name: "search", label: _t("Search Icon") },
            { name: "language", label: _t("Language Icon") },
        ],
    };

    setup() {
        if (!this.services.website.isDesigner) {
            return;
        }
        this.addDomListener(this.editable, "click", (ev) => {
            const iconEl = ev.target.closest(HEADER_ICON_SELECTOR);
            if (iconEl) {
                this.dependencies.media_website.openImageTooltip(iconEl);
            }
        });
        this.addDomListener(this.editable, "dblclick", (ev) => {
            const iconEl = ev.target.closest(HEADER_ICON_SELECTOR);
            if (iconEl) {
                this.dependencies.operation.next(() => this.replaceIcon(iconEl));
            }
        });
    }

    replaceIcon(iconEl) {
        return this.dependencies.media.openMediaDialog({
            visibleTabs: ["ICONS"],
            media: iconEl,
            save: (newIconEl) => {
                const name = iconEl.dataset.headerIcon;
                const sameIconEls = this.editable.querySelectorAll(`[data-header-icon="${name}"]`);
                for (const el of sameIconEls) {
                    el.dataset.icon = newIconEl.dataset.icon;
                    el.classList.toggle("oi-filled", newIconEl.classList.contains("oi-filled"));
                }
                this.dependencies.history.commit();
            },
        });
    }

    async onSave() {
        const iconEls = this.editable.querySelectorAll(`.${DIRTY_CLASS}`);
        if (!iconEls.length) {
            return;
        }
        const icons = {};
        for (const iconEl of iconEls) {
            icons[iconEl.dataset.headerIcon] = {
                icon: iconEl.dataset.icon,
                filled: iconEl.classList.contains("oi-filled"),
            };
        }
        await this.services.orm.call("website", "set_header_icons", [
            this.services.website.currentWebsite.id,
            icons,
        ]);
    }
}

export class ReplaceHeaderIconAction extends BuilderAction {
    static id = "replaceHeaderIcon";
    static dependencies = ["headerIcons"];

    setup() {
        this.canTimeout = false;
        this.preview = false;
    }

    async apply({ editingElement, params: { mainParam: name } }) {
        const iconEl = editingElement.querySelector(`[data-header-icon="${name}"]`);
        await this.dependencies.headerIcons.replaceIcon(iconEl);
    }
}

registry.category("website-plugins").add(HeaderIconsPlugin.id, HeaderIconsPlugin);
