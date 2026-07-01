/** @odoo-module **/
/* Phase 14 v3 - Salesforce-style 4-panel Report Builder.
 *
 * Layout:
 *   [ Data Sources ] [ Available Fields ] [ Builder Canvas ] [ Live Preview ]
 *
 * The component talks to mv.report's RPC methods (see
 * models/phase14_reports_rpc.py) for everything. Drag-and-drop uses
 * the native HTML5 DnD API - we set the dragged field id in
 * dataTransfer and let drop handlers route it to the right list. */

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

        // Static-action route passes the id via context; ad-hoc Python
        // return passes it via params. Accept either.
        const a = this.props.action || {};
        this.reportId = (a.params && a.params.report_id)
                     || (a.context && (a.context.report_id || a.context.active_id))
                     || null;
        this.state = useState({
            loaded: false,
            saving: false,
            previewLoading: false,
            // Saved-report fields the planner is editing.
            report: {
                id: this.reportId,
                name: "",
                description: "",
                model_id: null,
                model_name: "",
                model_tech: "",
                is_public: false,
                columns: [], filters: [], groups: [], sorts: [],
            },
            // Sidebar
            models: [],          // [{ id, name, tech, field_count }]
            selectedModelId: null,
            modelSearch: "",
            fields: [],          // [{ id, name, label, ttype, relation }]
            fieldSearch: "",
            // Preview state
            preview: { columns: [], rows: [], total: 0, limit: 20, offset: 0 },
            // Drag state - which field id is being dragged + from which zone
            dragField: null,
            dragSource: null,    // "fields" | "columns" | "filters" | "groups" | "sorts"
            dragIdx: null,       // for reorder within a zone
        });

        onWillStart(async () => {
            const [models, loaded] = await Promise.all([
                this.orm.call("mv.report", "report_get_models", []),
                this.orm.call("mv.report", "report_load", [this.reportId]),
            ]);
            this.state.models = models || [];
            if (loaded) {
                Object.assign(this.state.report, loaded);
                this.state.selectedModelId = loaded.model_id;
            }
            if (this.state.selectedModelId) {
                await this._loadFields(this.state.selectedModelId);
            }
            this.state.loaded = true;
            await this._refreshPreview();
        });
    }

    // ---- Data fetch -----------------------------------------------
    async _loadFields(modelId) {
        const fields = await this.orm.call(
            "mv.report", "report_get_fields", [modelId],
        );
        this.state.fields = fields || [];
    }

    async _refreshPreview() {
        if (!this.reportId) return;
        this.state.previewLoading = true;
        try {
            // Persist transient state first so the backend sees what
            // the user has on screen (silent save).
            await this._save(/*silent=*/true);
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
                    model_id: this.state.report.model_id,
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
        // 'ir.actions.act_window_close' only closes overlay dialogs.
        // The Report Builder is a top-level client action, so use the
        // browser history to step back one breadcrumb (which is the
        // form view of mv.report the user came from). Fall back to
        // the reports list if there's no history to pop.
        try {
            await this._save(/*silent=*/true);
        } catch (e) { /* don't block close on a save failure */ }
        if (window.history.length > 1) {
            window.history.back();
        } else {
            await this.action.doAction("marathon_ventures.action_mv_report");
        }
    }

    // ---- Model picker ----------------------------------------------
    async selectModel(modelId) {
        this.state.selectedModelId = modelId;
        const m = this.state.models.find((m) => m.id === modelId);
        this.state.report.model_id = modelId;
        this.state.report.model_name = m ? m.name : "";
        this.state.report.model_tech = m ? m.tech : "";
        // Clear previous selections - they reference fields from the
        // old model. Planner has to rebuild for the new source.
        this.state.report.columns = [];
        this.state.report.filters = [];
        this.state.report.groups = [];
        this.state.report.sorts = [];
        await this._loadFields(modelId);
        await this._refreshPreview();
    }
    get filteredModels() {
        const q = (this.state.modelSearch || "").toLowerCase().trim();
        if (!q) return this.state.models;
        return this.state.models.filter(
            (m) => m.name.toLowerCase().includes(q) || m.tech.toLowerCase().includes(q),
        );
    }
    get filteredFields() {
        const q = (this.state.fieldSearch || "").toLowerCase().trim();
        if (!q) return this.state.fields;
        return this.state.fields.filter(
            (f) => f.label.toLowerCase().includes(q) || f.name.toLowerCase().includes(q),
        );
    }

    // ---- DnD: source = fields panel --------------------------------
    onFieldDragStart(field, ev) {
        this.state.dragField = field;
        this.state.dragSource = "fields";
        ev.dataTransfer.effectAllowed = "copy";
        ev.dataTransfer.setData("text/plain", String(field.id));
    }

    // ---- DnD: drop zones (columns, filters, groups, sorts) ---------
    onDropColumn(ev) {
        ev.preventDefault();
        const f = this.state.dragField;
        if (!f) return;
        // If reorder (drag from columns zone) and the drop landed in
        // the zone background (not on a chip), move the dragged chip
        // to the end. Drop-on-chip is handled by onColumnDropOnItem.
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
        if (this.state.report.columns.some((c) => c.field_id === f.id)) return;
        this.state.report.columns.push({
            field_id: f.id,
            field_name: f.name,
            label: f.label,
            ttype: f.ttype,
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
        this.state.report.filters.push({
            field_id: f.id,
            field_name: f.name,
            label: f.label,
            ttype: f.ttype,
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
        if (this.state.report.groups.some((g) => g.field_id === f.id)) return;
        this.state.report.groups.push({
            field_id: f.id, field_name: f.name, label: f.label,
        });
        this._endDrag();
        this._refreshPreview();
    }
    onDropSort(ev) {
        ev.preventDefault();
        const f = this.state.dragField;
        if (!f || this.state.dragSource === "sorts") return;
        if (this.state.report.sorts.some((s) => s.field_id === f.id)) return;
        this.state.report.sorts.push({
            field_id: f.id, field_name: f.name, label: f.label, direction: "asc",
        });
        this._endDrag();
        this._refreshPreview();
    }
    onDragOver(ev) { ev.preventDefault(); ev.dataTransfer.dropEffect = "copy"; }

    // Per-chip dragover for the Columns zone - shows a drop indicator
    // on the chip being hovered, and sets dropEffect=move so the OS
    // cursor shows the move icon rather than copy.
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
        // Clear lingering drop-target highlights AND the dragging-dim
        // class that we put on directly in onColumnDragStart.
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
    removeColumn(idx) {
        this.state.report.columns.splice(idx, 1);
        this._refreshPreview();
    }
    removeFilter(idx) {
        this.state.report.filters.splice(idx, 1);
        this._refreshPreview();
    }
    removeGroup(idx) {
        this.state.report.groups.splice(idx, 1);
        this._refreshPreview();
    }
    removeSort(idx) {
        this.state.report.sorts.splice(idx, 1);
        this._refreshPreview();
    }
    onColumnLabelInput(idx, ev) {
        this.state.report.columns[idx].label = ev.target.value;
    }
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

    // ---- Reorder within a zone (column drag + drop) -----------------
    onColumnDragStart(idx, ev) {
        this.state.dragField = this.state.report.columns[idx];
        this.state.dragSource = "columns";
        this.state.dragIdx = idx;
        ev.dataTransfer.effectAllowed = "move";
        // Firefox requires setData on dragstart - without it, no
        // subsequent drop event fires anywhere. The actual payload
        // doesn't matter because the drop handlers read from state.
        ev.dataTransfer.setData("text/plain", String(idx));
        // The drag source is the ⋮⋮ handle, not the chip itself.
        // Walk up to the chip to apply the dragging-dim class AND
        // to use the chip as the visible drag preview (otherwise
        // the browser shows just the tiny handle).
        const handle = ev.currentTarget;
        const chip = handle && handle.closest
            ? handle.closest(".mv-rb__chip")
            : null;
        if (chip) {
            chip.classList.add("mv-rb__chip--dragging");
            // setDragImage requires a DOM node currently visible in
            // the document. The chip qualifies. Offset to roughly
            // where the user grabbed.
            try {
                const rect = chip.getBoundingClientRect();
                ev.dataTransfer.setDragImage(
                    chip, ev.clientX - rect.left, ev.clientY - rect.top,
                );
            } catch (e) { /* setDragImage not supported - ignore */ }
        }
    }
    onColumnDropOnItem(targetIdx, ev) {
        ev.preventDefault();
        // Clear hover highlight on the target chip.
        const tgt = ev.currentTarget;
        if (tgt) tgt.classList.remove("mv-rb__chip--drop-target");
        // CRITICAL: only stopPropagation when we actually handle the
        // event ourselves (i.e., this is a column-to-column reorder).
        // For a NEW field being dropped on an existing chip, we must
        // let the drop bubble up to the zone's onDropColumn so it can
        // add the field as a new column. Stopping propagation here
        // would silently swallow every drop after the first one.
        if (this.state.dragSource !== "columns") return;
        ev.stopPropagation();
        const from = this.state.dragIdx;
        if (from === null || from === targetIdx) {
            this._endDrag();
            return;
        }
        const cols = this.state.report.columns;
        const [moved] = cols.splice(from, 1);
        // Trello-style: drop A onto C => A takes C's position, C
        // shifts. splice(targetIdx,0,moved) gives that behavior.
        cols.splice(targetIdx, 0, moved);
        this._endDrag();
        this._refreshPreview();
    }

    // ---- Preview pagination ----------------------------------------
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
