// @ts-check
/** @odoo-module native */

import { Component, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { Dialog } from "@web/ui/dialog";

export class FieldWidgetsDialog extends Component {
    static components = { Dialog };
    static props = {
        close: Function,
    };
    static template = xml`
        <Dialog title="this.title" size="'lg'">
            <div class="o_field_widgets_inspector">
                <div class="d-flex align-items-center gap-2 mb-2">
                    <input
                        type="search"
                        class="form-control flex-grow-1"
                        t-att-placeholder="this.labels.filter"
                        t-model="this.state.filter"
                        autofocus="true"
                    />
                    <small class="text-muted text-nowrap">
                        <t t-out="this.filteredEntries.length"/> / <t t-out="this.entries.length"/>
                    </small>
                </div>
                <div class="table-responsive" style="max-height: 60vh">
                    <table class="table table-sm table-hover table-striped mb-0">
                        <thead class="position-sticky top-0 bg-white">
                            <tr>
                                <th t-out="this.labels.name"/>
                                <th t-out="this.labels.displayName"/>
                                <th t-out="this.labels.supportedTypes"/>
                                <th t-out="this.labels.component"/>
                                <th class="text-end" t-out="this.labels.options"/>
                            </tr>
                        </thead>
                        <tbody>
                            <tr t-foreach="this.filteredEntries" t-as="entry" t-key="entry[0]">
                                <td><code t-out="entry[0]"/></td>
                                <td t-out="this.displayName(entry[1])"/>
                                <td t-out="this.supportedTypes(entry[1])"/>
                                <td><code t-out="this.componentName(entry[1])"/></td>
                                <td class="text-end" t-out="this.optionCount(entry[1])"/>
                            </tr>
                            <tr t-if="!this.filteredEntries.length">
                                <td colspan="5" class="text-center text-muted py-3"
                                    t-out="this.labels.empty"/>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </Dialog>`;

    /** @type {{ filter: string }} */
    state;
    /** @type {[string, any][]} */
    entries;

    setup() {
        this.title = _t("Field Widgets");
        this.labels = {
            filter: _t("Filter by name, display name, or supported type…"),
            name: _t("Name"),
            displayName: _t("Display name"),
            supportedTypes: _t("Supported types"),
            component: _t("Component"),
            options: _t("Options"),
            empty: _t("No widgets match the filter."),
        };
        this.entries = [...registry.category("fields").getEntries()].sort(([a], [b]) =>
            a.localeCompare(b),
        );
        this.state = useState({ filter: "" });
    }

    get filteredEntries() {
        const filter = this.state.filter.trim().toLowerCase();
        if (!filter) {
            return this.entries;
        }
        return this.entries.filter(([key, value]) => {
            if (key.toLowerCase().includes(filter)) {
                return true;
            }
            const display = String(value?.displayName ?? "").toLowerCase();
            if (display.includes(filter)) {
                return true;
            }
            return (value?.supportedTypes ?? []).some((t) =>
                String(t).toLowerCase().includes(filter),
            );
        });
    }

    displayName(value) {
        return String(value?.displayName ?? "—");
    }

    supportedTypes(value) {
        const types = value?.supportedTypes ?? [];
        return types.length ? types.join(", ") : "—";
    }

    componentName(value) {
        return value?.component?.name ?? "—";
    }

    optionCount(value) {
        return value?.supportedOptions?.length ?? 0;
    }
}
