import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

/**
 * Lets a website designer show/hide, reorder and add columns of the portal
 * document tables rendered through ``portal.portal_list_table``. The effective
 * column set is stored per model in ``portal.list.column`` and re-applied
 * server-side on the next render (see CustomerPortal._apply_portal_list_columns).
 */
export class PortalListOptionPlugin extends Plugin {
    static id = "portalListOption";
    static shared = ["loadColumns", "getColumns", "updateColumns"];
    resources = {
        builder_actions: {
            UpdatePortalListColumnsAction,
            ToggleEmptyMessageAction,
        },
        on_will_save_handlers: this.savePortalListColumns.bind(this),
        clean_for_save_processors: this.cleanForSave.bind(this),
    };

    cleanForSave(root) {
        for (const el of root.querySelectorAll(".o_portal_list_empty, .o_portal_list_filled")) {
            el.classList.remove("o_enable_preview", "o_disable_preview");
        }
        return root;
    }

    getColumns() {
        return this.columns || [];
    }

    async loadColumns(tableEl) {
        if (this.tableEl === tableEl) {
            return this.columnChoices;
        }
        const modelName = tableEl.dataset.listModel;
        const listRef = tableEl.dataset.listRef;

        // A header cell can have a blank label (e.g. the "Pay Now" column), so
        // fall back to the column id to keep the row identifiable.
        const visible = [...tableEl.querySelectorAll("th[name]")].map((th) => ({
            id: th.getAttribute("name"),
            display_name: th.textContent.trim() || th.getAttribute("name"),
            added: th.dataset.added === "1",
        }));

        const [overrides, availableFields] = await Promise.all([
            // Stored customization: hidden built-ins + definitions of added fields.
            this.services.orm.searchRead(
                "portal.list.column",
                [["list_ref", "=", listRef]],
                ["name", "field_name", "show_in_portal"]
            ),
            this.services.orm.call("portal.list.column", "get_available_fields", [modelName]),
        ]);

        this.builtinColumns = new Set(
            visible.filter((column) => !column.added).map((column) => column.id)
        );
        // Every built-in of the list, including the ones the current rendering
        // leaves out (e.g. the column the list is grouped by): re-adding such a
        // column has to restore its built-in rendering instead of turning it
        // into a plain model field.
        this.builtinNames = new Set((tableEl.dataset.listBuiltins || "").split(","));
        const hiddenBuiltins = [];
        for (const override of overrides) {
            if (!override.field_name && !override.show_in_portal) {
                this.builtinColumns.add(override.name);
                // A hidden column has no header left to read a label from.
                hiddenBuiltins.push({
                    id: override.name,
                    display_name: override.name,
                });
            }
        }

        for (const name of this.builtinColumns) {
            this.builtinNames.add(name);
        }

        this.columns = visible.map((c) => ({ id: c.id, display_name: c.display_name }));

        // Choices = included ∪ hidden built-ins ∪ available fields
        // (built-in wins on id clash).
        const choicesById = new Map();
        for (const item of [...this.columns, ...hiddenBuiltins]) {
            choicesById.set(item.id, { id: item.id, display_name: item.display_name });
        }
        for (const field of availableFields) {
            if (!choicesById.has(field.id)) {
                choicesById.set(field.id, { id: field.id, display_name: field.display_name });
            }
        }
        this.columnChoices = [...choicesById.values()];
        this.listRef = listRef;
        this.tableEl = tableEl;
        return this.columnChoices;
    }

    updateColumns(columns) {
        this.columns = columns;
        this.hasPendingChanges = true;
    }

    async savePortalListColumns() {
        if (!this.hasPendingChanges) {
            return;
        }
        const shown = new Set(this.columns.map((c) => c.id));
        const records = this.columns.map((column, index) => {
            const isField = !this.builtinNames.has(column.id);
            return {
                name: column.id,
                sequence: (index + 1) * 10,
                show_in_portal: true,
                field_name: isField ? column.id : false,
            };
        });
        for (const name of this.builtinColumns) {
            if (!shown.has(name)) {
                records.push({
                    name,
                    sequence: 0,
                    show_in_portal: false,
                    field_name: false,
                });
            }
        }
        await this.services.orm.call("portal.list.column", "replace_configuration", [
            this.listRef,
            records,
        ]);
        this.hasPendingChanges = false;
    }
}

export class UpdatePortalListColumnsAction extends BuilderAction {
    static id = "updatePortalListColumns";
    static dependencies = ["portalListOption"];

    setup() {
        this.preview = false;
        // Added columns can only be rendered server-side, so persist and reload
        // on every change rather than attempting a partial client preview.
        this.reload = {};
    }
    async prepare({ editingElement }) {
        await this.dependencies.portalListOption.loadColumns(editingElement);
    }
    getValue() {
        return JSON.stringify(this.dependencies.portalListOption.getColumns());
    }
    apply({ value }) {
        this.dependencies.portalListOption.updateColumns(JSON.parse(value));
    }
}

export class ToggleEmptyMessageAction extends BuilderAction {
    static id = "toggleEmptyMessage";

    apply({ editingElement }) {
        this.setEmptyMessageVisibility(editingElement, true);
    }
    clean({ editingElement }) {
        this.setEmptyMessageVisibility(editingElement, false);
    }
    isApplied({ editingElement }) {
        const emptyEl = editingElement.querySelector(".o_portal_list_empty");
        return !!emptyEl && emptyEl.classList.contains("o_enable_preview");
    }
    setEmptyMessageVisibility(editingElement, isVisible) {
        const emptyEl = editingElement.querySelector(".o_portal_list_empty");
        const tableEl = editingElement.querySelector(".o_portal_list_filled");
        emptyEl.classList.toggle("o_enable_preview", isVisible);
        emptyEl.classList.toggle("o_disable_preview", !isVisible);
        tableEl.classList.toggle("o_enable_preview", !isVisible);
        tableEl.classList.toggle("o_disable_preview", isVisible);
    }
}

registry.category("website-plugins").add(PortalListOptionPlugin.id, PortalListOptionPlugin);
