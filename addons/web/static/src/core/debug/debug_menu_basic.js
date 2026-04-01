import { useEnvDebugContext } from "./debug_context";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { groupBy, sortBy } from "@web/core/utils/arrays";

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

const debugSectionRegistry = registry.category("debug_section");

debugSectionRegistry
    .add("record", { label: _t("Record"), sequence: 10 })
    .add("records", { label: _t("Records"), sequence: 10 })
    .add("ui", { label: _t("User Interface"), sequence: 20 })
    .add("security", { label: _t("Security"), sequence: 30 })
    .add("testing", { label: _t("Tours & Testing"), sequence: 40 })
    .add("tools", { label: _t("Tools"), sequence: 50 });

export class DebugMenuBasic extends Component {
    static template = "web.DebugMenu";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {};

    setup() {
        this.debugContext = useEnvDebugContext();
    }

    async loadGroupedItems() {
        const items = await this.debugContext.getItems(this.env);
        const sections = groupBy(items, (item) => item.section || "");
        this.sectionEntries = sortBy(
            Object.entries(sections),
            ([section]) => debugSectionRegistry.get(section, { sequence: 50 }).sequence
        );
    }

    getSectionLabel(section) {
        return debugSectionRegistry.get(section, { label: section }).label;
    }
}
