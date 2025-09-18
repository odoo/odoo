// @ts-check

/** @module @web/services/debug/debug_menu_basic - Base debug menu dropdown grouped by section (Record, UI, Security, etc.) */

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { groupBy, sortBy } from "@web/core/utils/collections/arrays";

import { useEnvDebugContext } from "./debug_context";

const debugSectionRegistry = registry.category("debug_section");

debugSectionRegistry
    .add("record", { label: _t("Record"), sequence: 10 })
    .add("records", { label: _t("Records"), sequence: 10 })
    .add("ui", { label: _t("User Interface"), sequence: 20 })
    .add("security", { label: _t("Security"), sequence: 30 })
    .add("testing", { label: _t("Tours & Testing"), sequence: 40 })
    .add("tools", { label: _t("Tools"), sequence: 50 });

/**
 * Base debug menu component that renders debug items grouped by section.
 * Subclassed by `DebugMenu` which adds command palette integration.
 */
export class DebugMenuBasic extends Component {
    static template = "web.DebugMenu";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {};

    setup() {
        /** @type {any} */
        this.debugContext = useEnvDebugContext();
    }

    /**
     * Load debug items from the debug context and group them by section.
     * Sets `this.sectionEntries` as sorted [section, items[]] pairs.
     * @returns {Promise<void>}
     */
    async loadGroupedItems() {
        const items = await this.debugContext.getItems(this.env);
        const sections = groupBy(items, (item) => item.section || "");
        this.sectionEntries = sortBy(
            Object.entries(sections),
            ([section]) =>
                debugSectionRegistry.get(section, /** @type {any} */ ({ sequence: 50 }))
                    .sequence,
        );
    }

    /**
     * Get the display label for a debug menu section.
     * @param {string} section - the section key
     * @returns {string}
     */
    getSectionLabel(section) {
        return debugSectionRegistry.get(
            section,
            /** @type {any} */ ({ label: section }),
        ).label;
    }
}
