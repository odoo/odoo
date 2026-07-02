/** @odoo-module **/
/* Phase 14 v4 - Salesforce-style Report Builder over Report Types.
 *
 * Layout:
 *   [ Data Sources ]  <- Report Types (not raw models any more)
 *   [ Available Fields ]  <- grouped by node (Base + each Joined model)
 *   [ Builder Canvas ]  <- Selected Columns / Filters / Group By / Sort
 *   [ Live Preview ]
 *
 * v4 key differences vs. v3:
 *   - state.reportTypes replaces state.models.
 *   - state.fieldNodes replaces state.fields; it's a list of node
 *     descriptors each with its own fields[]. Preserves grouping and
 *     path prefixes end-to-end.
 *   - Every selection (column/filter/group/sort) stores an absolute
 *     `path` string. The backend uses the path to walk/join relations. */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class MvReportBuilder extends Component {
    static template = "marathon_ventures.MvReportBuilder";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        const a = this.props.action || {};
        this.reportId = (a.params && a.params.report_id)
                     || (a.context && (a.context.report_id || a.context.active_id))
                     || null;

        this.state = useState({
            loaded: false,
            saving: false,
            previewLoading: false,
            report: {
                id: this.reportId,
                name: "",
                description: "",
                report_type_id: null,
                report_type_name: "",
                model_id: null,
                model_tech: "",
                is_public: false,
                columns: [], filters: [], groups: [], sorts: [],
            },
            // Sidebar
            reportTypes: [],       // [{ id, name, description, base_model_tech, ... }]
            reportTypeSearch: "",
            selectedReportTypeId: null,
            // Fields (grouped by node)
            fieldNodes: [],        // [{ node_id, label, model_tech, path_prefix, fields: [...] }]
            fieldSearch: "",
            // Preview
            preview: { columns: [], rows: [], total: 0, limit: 20, offset: 0 },
            // Drag state
            dragField: null,       // in v4 this holds the full field dict {id, name, label, ttype, path, node_id}
            dragSource: null,      // "fields" | "columns" | "filters" | "groups" | "sorts"
            dragIdx: null,
        });

        onWillStart(async () => {
            const [types, loaded] = await Promise.all([
                this.orm.call("mv.report", "report_type_get_all", []),
                this.orm.call("mv.report", "report_load", [this.reportId]),
            ]);
            this.state.reportTypes = types || [];
            if (loaded) {
                Object.assign(this.state.report, loaded);
                this.state.selectedReportTypeId = loaded.report_type_id || null;
            }
            if (this.state.selectedReportTypeId) {
                await this._loadFieldsForType(this.state.selectedReportTypeId);
            }
            this.state.loaded = true;
            await this._refreshPreview();
        });
    }

    // ---- Data fetch -----------------------------------------------
    async _loadFieldsForType(rtId) {
        const data = await this.orm.call(
            "mv.report", "report_type_get_fields", [rtId],
        );
        this.state.fieldNodes = (data && data.nodes) || [];
    }

    async _refreshPreview() {
        if (!this.reportId) return;
        this.state.previewLoading = true;
        try {
            await this._save(true);
            const data = await this.orm.call(
                "mv.report", "report_preview",
                [this.reportId, this.state.preview.limit, this.state.preview.offset],
            );
            Object.assign(this.state.preview, data);
        } finally {
            this.state.previewLoading = false;
        }
    }

    async _save(silent) {
        this.state.saving = true;
        try {
            await this.orm.call("mv.report", "report_save", [
                this.reportId,
                {
                    name: this.state.report.name,
                    description: this.state.report.description,
                    report_type_id: this.state.report.report_type_id,
                    is_public: this.state.report.is_public,
                    columns: this.state.report.columns,
                    filters: this.state.report.filters,
                    groups: this.state.report.groups,
                    sorts: this.state.report.sorts,
                },
            ]);
            if (!silent) {
                this.notification.add("Report saved", { type: "success" });
            }
        } finally {
            this.state.saving = false;
        }
    }

    // ---- Header handlers ------------------------------------------
    onNameInput(ev) { this.state.report.name = ev.target.value; }
    onDescInput(ev) { this.state.report.description = ev.target.value; }
    async onSave() { await this._save(false); await this._refreshPreview(); }
    async onSaveAndRun() {
        await this._save(true);
        await this.onRun();
    }
    async onRun() {
        const action = await this.orm.call("mv.report", "action_run", [this.reportId]);
        this.action.doAction(action);
    }
    async onClose() {
        try { await this._save(true); } catch (e) { /* don't block close */ }
        if (window.history.length > 1) {
            window.history.back();
        } else {
            await this.action.doAction("marathon_ventures.action_mv_report");
        }
    }

    // ---- Report Type picker ---------------------------------------
    async selectReportType(rtId) {
        // v4 semantics: switching Report Type PRESERVES the current
        // columns / filters / groups / sorts (they'll be re-evaluated
        // against the new type's fields on the next preview). This is
        // the whole point of Report Types - fields are keyed by
        // absolute path, so they stay valid as long as the path still
        // resolves in the new type.
        this.state.selectedReportTypeId = rtId;
        const rt = this.state.reportTypes.find((r) => r.id === rtId);
        this.state.report.report_type_id = rtId;
        this.state.report.report_type_name = rt ? rt.name : "";
        this.state.report.model_id = rt ? rt.base_model_id : null;
        this.state.report.model_tech = rt ? rt.base_model_tech : "";
        await this._loadFieldsForType(rtId);
        await this._refreshPreview();
    }
    get filteredReportTypes() {
        const q = (this.state.reportTypeSearch || "").toLowerCase().trim();
        if (!q) return this.state.reportTypes;
        return this.state.reportTypes.filter(
            (r) => r.name.toLowerCase().includes(q)
                || r.base_model_tech.toLowerCase().includes(q)
                || (r.description || "").toLowerCase().includes(q),
        );
    }
    get filteredFieldNodes() {
        const q = (this.state.fieldSearch || "").toLowerCase().trim();
        if (!q) return this.state.fieldNodes;
        return this.state.fieldNodes
            .map((node) => ({
                ...node,
                fields: node.fields.filter(
                    (f) => f.label.toLowerCase().includes(q)
                        || f.name.toLowerCase().includes(q)
                        || f.path.toLowerCase().includes(q),
                ),
            }))
            .filter((node) => node.fields.length > 0);
    }

    // ---- DnD: source = fields panel --------------------------------
    onFieldDragStart(field, ev) {
        this.state.dragField = field;
        this.state.dragSource = "fields";
        ev.dataTransfer.effectAllowed = "copy";
        ev.dataTransfer.setData("text/plain", String(field.id));
    }

    // ---- DnD: drop zones -------------------------------------------
    onDropColumn(ev) {
        ev.preventDefault();
        const f = this.state.dragField;
        if (!f) return;
        if (this.state.dragSource === "columns") {
            const from = this.state.dragIdx;
            const cols = this.state.report.columns;
            if (from !== null && from !== cols.length - 1) {
                const [moved] = cols.splice(from, 1);
                cols.push(moved);
                this._endDrag();
                this._refreshPreview();
            } else {
                this._endDrag();
            }
            return;
        }
        // Dedupe by full path (not just field_id, since the same
        // terminal field can appear at different paths in a multi-
        // node report type).
        if (this.state.report.columns.some((c) => c.path === f.path)) return;
        this.state.report.columns.push({
            field_id: f.id,
            field_name: f.name,
            label: f.label,
            ttype: f.ttype,
            path: f.path,
            node_id: f.node_id || false,
            aggregation: "none",
        });
        this._endDrag();
        this._refreshPreview();
    }
    onDropFilter(ev) {
        ev.preventDefault();
        const f = this.state.dragField;
        if (!f) return;
        if (this.state.dragSource === "filters") return;
        // Copy `selection` too so the template can render a proper
        // <select> for selection-type fields without a round-trip.
        this.state.report.filters.push({
            field_id: f.id,
            field_name: f.name,
            label: f.label,
            ttype: f.ttype,
            selection: f.selection || null,
            path: f.path,
            node_id: f.node_id || false,
            operator: f.ttype === 'char' ? 'ilike' : '=',
            value: "",
            logical_op: "and",
        });
        this._endDrag();
        this._refreshPreview();
    }
    onDropGroup(ev) {
        ev.preventDefault();
        const f = this.state.dragField;
        if (!f || this.state.dragSource === "groups") return;
        if (this.state.report.groups.some((g) => g.path === f.path)) return;
        this.state.report.groups.push({
            field_id: f.id, field_name: f.name, label: f.label,
            path: f.path, node_id: f.node_id || false,
        });
        this._endDrag();
        this._refreshPreview();
    }
    onDropSort(ev) {
        ev.preventDefault();
        const f = this.state.dragField;
        if (!f || this.state.dragSource === "sorts") return;
        if (this.state.report.sorts.some((s) => s.path === f.path)) return;
        this.state.report.sorts.push({
            field_id: f.id, field_name: f.name, label: f.label,
            path: f.path, node_id: f.node_id || false,
            direction: "asc",
        });
        this._endDrag();
        this._refreshPreview();
    }
    onDragOver(ev) { ev.preventDefault(); ev.dataTransfer.dropEffect = "copy"; }

    onColumnDragOverItem(idx, ev) {
        ev.preventDefault();
        if (this.state.dragSource === "columns") {
            ev.dataTransfer.dropEffect = "move";
            const el = ev.currentTarget;
            if (el) el.classList.add("mv-rb__chip--drop-target");
        } else {
            ev.dataTransfer.dropEffect = "copy";
        }
    }
    onColumnDragLeaveItem(idx, ev) {
        const el = ev.currentTarget;
        if (el) el.classList.remove("mv-rb__chip--drop-target");
    }

    _endDrag(ev) {
        document.querySelectorAll(".mv-rb__chip--drop-target").forEach(
            (el) => el.classList.remove("mv-rb__chip--drop-target"),
        );
        document.querySelectorAll(".mv-rb__chip--dragging").forEach(
            (el) => el.classList.remove("mv-rb__chip--dragging"),
        );
        this.state.dragField = null;
        this.state.dragSource = null;
        this.state.dragIdx = null;
    }

    // ---- Item operations ------------------------------------------
    removeColumn(idx) { this.state.report.columns.splice(idx, 1); this._refreshPreview(); }
    removeFilter(idx) { this.state.report.filters.splice(idx, 1); this._refreshPreview(); }
    removeGroup(idx) { this.state.report.groups.splice(idx, 1); this._refreshPreview(); }
    removeSort(idx) { this.state.report.sorts.splice(idx, 1); this._refreshPreview(); }
    onColumnLabelInput(idx, ev) { this.state.report.columns[idx].label = ev.target.value; }
    onColumnAggSelect(idx, ev) {
        this.state.report.columns[idx].aggregation = ev.target.value;
        this._refreshPreview();
    }
    onFilterOpSelect(idx, ev) {
        this.state.report.filters[idx].operator = ev.target.value;
        this._refreshPreview();
    }
    onFilterValueInput(idx, ev) {
        this.state.report.filters[idx].value = ev.target.value;
        this._refreshPreview();
    }
    onSortDirSelect(idx, ev) {
        this.state.report.sorts[idx].direction = ev.target.value;
        this._refreshPreview();
    }

    // ---- Reorder within columns zone ------------------------------
    onColumnDragStart(idx, ev) {
        this.state.dragField = this.state.report.columns[idx];
        this.state.dragSource = "columns";
        this.state.dragIdx = idx;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", String(idx));
        const handle = ev.currentTarget;
        const chip = handle && handle.closest
            ? handle.closest(".mv-rb__chip")
            : null;
        if (chip) {
            chip.classList.add("mv-rb__chip--dragging");
            try {
                const rect = chip.getBoundingClientRect();
                ev.dataTransfer.setDragImage(
                    chip, ev.clientX - rect.left, ev.clientY - rect.top,
                );
            } catch (e) { /* ignore */ }
        }
    }
    onColumnDropOnItem(targetIdx, ev) {
        ev.preventDefault();
        const tgt = ev.currentTarget;
        if (tgt) tgt.classList.remove("mv-rb__chip--drop-target");
        if (this.state.dragSource !== "columns") return;
        ev.stopPropagation();
        const from = this.state.dragIdx;
        if (from === null || from === targetIdx) {
            this._endDrag();
            return;
        }
        const cols = this.state.report.columns;
        const [moved] = cols.splice(from, 1);
        cols.splice(targetIdx, 0, moved);
        this._endDrag();
        this._refreshPreview();
    }

    // ---- Preview pagination ---------------------------------------
    async previewPrev() {
        if (this.state.preview.offset <= 0) return;
        this.state.preview.offset = Math.max(
            0, this.state.preview.offset - this.state.preview.limit,
        );
        await this._refreshPreview();
    }
    async previewNext() {
        const { offset, limit, total } = this.state.preview;
        if (offset + limit >= total) return;
        this.state.preview.offset = offset + limit;
        await this._refreshPreview();
    }
}

registry.category("actions").add("mv_report_builder", MvReportBuilder);
