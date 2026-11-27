import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { normalizeCSSColor } from "@web/core/utils/colors";
import { CustomizeWebsiteColorAction } from "@website/builder/plugins/customize_website_plugin";

export class PortalOptionPlugin extends Plugin {
    static id = "portalOption";
    static dependencies = ["customizeWebsite", "domObserver"];
    static shared = ["getPortalCards", "loadPortalCards", "updatePortalCards", "setPortalCardIcon"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetStylePortalCardAction,
            SetPortalCardGapAction,
            UpdatePortalCardListAction,
            ReplacePortalCardIconAction,
            CustomizePortalIconColorAction,
        },
        anchor_excluded_selectors: ".o_portal_index_card",
        properties: { predicate: ".o_portal_index_card > *", immutableLink: true },
        on_will_save_handlers: this.savePortalOptions.bind(this),
    };

    setup() {
        this.cardIcons = new Map();
    }

    getPortalCards() {
        return this.portalCards;
    }

    async loadPortalCards() {
        if (!this.portalCards) {
            const entries = await this.services.orm.searchRead(
                "portal.entry",
                [["category", "!=", "alert"]],
                ["name", "id", "sequence", "show_in_portal"]
            );
            this.portalCards = entries.filter((entry) => {
                const cardEl = this.document.querySelector(
                    `.o_portal_index_card[data-id='${entry.id}']`
                );
                // Cards still hidden by business logic, such as unavailable
                // payment methods, are omitted from the option.
                return (
                    cardEl &&
                    (cardEl.dataset.hiddenByBusinessRule !== "1" ||
                        !cardEl.classList.contains("d-none"))
                );
            });
        }
        return this.portalCards;
    }

    async updatePortalCards(entries) {
        const previousEntries = this.portalCards;
        const hadPendingChanges = this.hasPendingChanges;
        this.portalCards = entries;
        this.hasPendingChanges = true;
        this.applyPortalCardsToDOM(entries);
        this.dependencies.domObserver.stageCustomMutation({
            apply: () => {
                this.portalCards = entries;
                this.hasPendingChanges = true;
                this.applyPortalCardsToDOM(entries);
            },
            revert: () => {
                this.portalCards = previousEntries;
                this.hasPendingChanges = hadPendingChanges;
                this.applyPortalCardsToDOM(previousEntries);
            },
        });
    }

    applyPortalCardsToDOM(entries) {
        const portalCardsEl = this.document.querySelector(".o_portal_cards");
        if (!portalCardsEl) {
            return;
        }
        for (const entry of entries) {
            const cardEl = portalCardsEl.querySelector(
                `.o_portal_index_card[data-id='${entry.id}']`
            );
            if (!cardEl) {
                continue;
            }
            cardEl.dataset.showInPortal = entry.show_in_portal;
            // Use the static template attribute rather than the current d-none class,
            // which is stale on undo/redo replay.
            const hiddenByBusinessRule = cardEl.dataset.hiddenByBusinessRule === "1";
            cardEl.classList.toggle("d-none", !entry.show_in_portal || hiddenByBusinessRule);
            portalCardsEl.append(cardEl);
        }
    }

    setPortalCardIcon(iconWrapperEl, icon) {
        const entryId = parseInt(iconWrapperEl.closest(".o_portal_index_card").dataset.id);
        const previousNodes = [...iconWrapperEl.childNodes];
        const previousIcon = this.cardIcons.get(entryId);
        const iconEl = this.document.createElement("i");
        iconEl.className = "oi oi-lg";
        iconEl.setAttribute("role", "img");
        iconEl.setAttribute("aria-hidden", "true");
        iconEl.dataset.icon = icon;
        const setIcon = (nodes, value) => {
            // The card comes from its portal.entry, its template must not be saved
            this.dependencies.domObserver.ignore(() => iconWrapperEl.replaceChildren(...nodes));
            if (value) {
                this.cardIcons.set(entryId, value);
            } else {
                this.cardIcons.delete(entryId);
            }
        };
        setIcon([iconEl], icon);
        this.dependencies.domObserver.stageCustomMutation({
            apply: () => setIcon([iconEl], icon),
            revert: () => setIcon(previousNodes, previousIcon),
        });
    }

    async savePortalOptions() {
        const valsById = new Map();
        if (this.hasPendingChanges) {
            this.portalCards.forEach((entry, index) =>
                valsById.set(entry.id, {
                    sequence: (index + 1) * 10,
                    show_in_portal: entry.show_in_portal,
                })
            );
        }
        for (const [id, icon] of this.cardIcons) {
            valsById.set(id, { ...valsById.get(id), icon });
        }
        if (valsById.size) {
            await this.services.orm.webSaveMulti(
                "portal.entry",
                [...valsById.keys()],
                [...valsById.values()],
                { specification: {} }
            );
        }
        const portalCardGap =
            this.document.documentElement.style.getPropertyValue("--portal-card-gap");
        if (portalCardGap) {
            await this.dependencies.customizeWebsite.customizeWebsiteVariables(
                { "portal-card-gap": portalCardGap },
                "null",
                false,
                false
            );
        }
    }
}

export class SetPortalCardGapAction extends BuilderAction {
    static id = "setPortalCardGap";
    static dependencies = ["customizeWebsite", "domObserver"];

    getValue() {
        return (
            this.document.documentElement.style.getPropertyValue("--portal-card-gap") ||
            this.dependencies.customizeWebsite.getWebsiteVariableValue("portal-card-gap")
        );
    }

    apply({ isPreviewing, value }) {
        const previousValue = this.getValue();
        this.setGap(value);
        if (!isPreviewing) {
            this.dependencies.domObserver.stageCustomMutation({
                apply: () => this.setGap(value),
                revert: () => this.setGap(previousValue),
            });
        }
    }

    setGap(value) {
        this.document.documentElement.style.setProperty("--portal-card-gap", value);
    }
}

export class SetStylePortalCardAction extends StyleAction {
    static id = "setStylePortalCard";
    static dependencies = ["customizeWebsite", "color"];

    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    /**
     * Applies the specified style to portal cards.
     *
     * @param {Object} params - Contains mainParam with the CSS property name
     * @param {string} value - The value to apply for the style property
     *
     */
    async apply({ params, value }) {
        const styleName = params.mainParam;
        const variableMap = {
            "border-style": "portal-card-border-style",
            "border-radius": "portal-card-border-radius",
            "border-width": "portal-card-border-width",
            "border-color": "portal-card-border-color",
        };

        if (styleName in variableMap) {
            if (styleName === "border-color") {
                return this.dependencies.customizeWebsite.customizeWebsiteColors({
                    [variableMap[styleName]]: value,
                });
            }
            return this.dependencies.customizeWebsite.customizeWebsiteVariables({
                [variableMap[styleName]]: value,
            });
        }
    }
}

export class UpdatePortalCardListAction extends BuilderAction {
    static id = "updatePortalCardList";
    static dependencies = ["portalOption"];

    setup() {
        this.preview = false;
    }
    async prepare() {
        await this.dependencies.portalOption.loadPortalCards();
    }
    apply({ editingElement, value }) {
        return this.dependencies.portalOption.updatePortalCards(JSON.parse(value), editingElement);
    }
    getValue() {
        return JSON.stringify(this.dependencies.portalOption.getPortalCards());
    }
}

export class CustomizePortalIconColorAction extends CustomizeWebsiteColorAction {
    static id = "customizePortalIconColor";

    getValue(context) {
        // Without a custom color, show the one the icon is rendered with
        const property =
            context.params.mainParam === "portal-icon-bg-color" ? "background-color" : "color";
        return (
            super.getValue(context) ||
            normalizeCSSColor(getComputedStyle(context.editingElement).getPropertyValue(property))
        );
    }
}

export class ReplacePortalCardIconAction extends BuilderAction {
    static id = "replacePortalCardIcon";
    static dependencies = ["media", "portalOption"];

    load({ editingElement }) {
        return new Promise((resolve) => {
            const media = document.createElement("i");
            media.className = "oi";
            media.dataset.icon = editingElement.querySelector("[data-icon]")?.dataset.icon || "";
            const onClose = this.dependencies.media.openMediaDialog(
                { visibleTabs: ["ICONS"], media, save: resolve },
                this.editable
            );
            onClose.then(resolve);
        });
    }
    apply({ editingElement, loadResult: iconEl }) {
        if (iconEl) {
            this.dependencies.portalOption.setPortalCardIcon(editingElement, iconEl.dataset.icon);
        }
    }
}

registry.category("website-plugins").add(PortalOptionPlugin.id, PortalOptionPlugin);
