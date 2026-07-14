/** @odoo-module **/

/*  Data Loader Wizard (Phase 17b)
 *  ------------------------------------------------------------
 *  Replaces the classic mv.dataloader.job form with a 5-step OWL
 *  wizard: Mode -> Source -> Map -> Preview -> Run. Drag-and-drop
 *  upload, live column mapping, per-row preview with error tooltips,
 *  final results screen with error CSV download.
 *
 *  The component is a field widget bound to the record's `id`
 *  field so it can take over the full form sheet while still
 *  getting the record context from the form controller. All
 *  server calls go through `orm.call('mv.dataloader.job', ...)`
 *  using the backend RPCs added in phase17_dataloader.py.
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const MODE_META = [
    { value: "insert", label: "Insert",
      hint:  "Create brand-new records from your CSV.",
      icon:  "fa-plus-circle" },
    { value: "update", label: "Update",
      hint:  "Overwrite fields on existing records matched by a key.",
      icon:  "fa-pencil-square-o" },
    { value: "upsert", label: "Upsert",
      hint:  "Update if a match exists, otherwise create.",
      icon:  "fa-refresh" },
    { value: "delete", label: "Delete",
      hint:  "Delete existing records matched by a key.",
      icon:  "fa-trash-o" },
    { value: "export", label: "Export",
      hint:  "Download filtered records as CSV.",
      icon:  "fa-download" },
];

// Step machine. Export skips steps 3 + 4 (mapping / preview).
const STEP_LABELS = [
    { n: 1, label: "Mode" },
    { n: 2, label: "Source" },
    { n: 3, label: "Map" },
    { n: 4, label: "Preview" },
    { n: 5, label: "Run" },
];

export class MvDataloaderWizard extends Component {
    static template = "marathon_ventures.MvDataloaderWizard";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notif = useService("notification");
        this.MODES = MODE_META;
        this.STEP_LABELS = STEP_LABELS;
        this.state = useState({
            loading: true,
            step: 1,
            error: "",           // top-level error banner
            models: [],          // {id, name, model}
            targetFields: [],    // fields on the selected model
            snap: null,          // dl_snapshot() payload
            filterModel: "",     // model-picker search
            filterField: "",     // field-picker search
            uploading: false,
            executing: false,
            dragOver: false,
            previewLimit: 25,
        });
        onWillStart(this.loadInitial.bind(this));
    }

    // ------------------------------------------------------------
    // Initial load
    // ------------------------------------------------------------
    get dealId() { return this.props.record && this.props.record.resId; }

    async loadInitial() {
        try {
            const id = this.dealId;
            const [models, snap] = await Promise.all([
                this.orm.call("mv.dataloader.job", "dl_list_models", [], {}),
                id
                    ? this.orm.call("mv.dataloader.job", "dl_snapshot", [[id]], {})
                    : Promise.resolve(this._blankSnap()),
            ]);
            this.state.models = models;
            this.state.snap = snap;
            if (snap.model_id) {
                this.state.targetFields = await this.orm.call(
                    "mv.dataloader.job", "dl_list_fields", [snap.model_id], {},
                );
            }
            // If job already has state past draft, jump to the right step
            this.state.step = this._stepForState(snap);
        } catch (e) {
            this.state.error = this._msg(e);
        } finally {
            this.state.loading = false;
        }
    }

    _blankSnap() {
        return {
            id: 0, name: "(new)", mode: "insert", state: "draft",
            model_id: false, model_name: "", model_label: "",
            source_filename: "", has_file: false,
            header_row: true, delimiter: ",",
            match_field_id: false, match_field_name: "", match_by: "value",
            on_error: "skip",
            export_domain: "[]", export_field_ids: [],
            exported_filename: "", has_export: false,
            total_rows: 0, success_count: 0, error_count: 0, skip_count: 0,
            started_at: false, finished_at: false, duration_seconds: 0,
            has_error_report: false, error_report_filename: "",
            mapping: [], lines: [],
        };
    }

    _stepForState(snap) {
        // Landing step given the job's persisted state.
        if (snap.state === "done" || snap.state === "failed") return 5;
        if (snap.state === "running")   return 5;
        if (snap.state === "previewed") return 4;
        if (snap.state === "mapped")    return 3;
        if (snap.mode === "export" && snap.model_id) return 5;
        if (snap.has_file || snap.model_id) return 2;
        return 1;
    }

    _msg(e) {
        if (!e) return "";
        return e.data && e.data.message ? e.data.message : (e.message || String(e));
    }

    // ------------------------------------------------------------
    // Step navigation
    // ------------------------------------------------------------
    isImport() {
        return this.state.snap && this.state.snap.mode !== "export";
    }

    visibleSteps() {
        if (this.isImport()) return STEP_LABELS;
        // Export: hide Map + Preview
        return STEP_LABELS.filter((s) => s.n === 1 || s.n === 2 || s.n === 5);
    }

    canGoNext() {
        const s = this.state.snap;
        if (!s) return false;
        switch (this.state.step) {
            case 1: return !!s.mode;
            case 2:
                if (s.mode === "export") return !!s.model_id;
                if (!s.model_id || !s.has_file) return false;
                if (["update","upsert","delete"].includes(s.mode) && !s.match_field_id) return false;
                return true;
            case 3: return s.mapping.some((m) => !m.skip && m.target_field_id);
            case 4: return true;
            default: return false;
        }
    }

    async onNext() {
        if (!this.canGoNext()) return;
        // Advance rules
        if (this.state.step === 2 && this.isImport()) {
            await this.saveJob({});   // ensure server-side state matches
            await this.doAutomap();
            this.state.step = 3;
            return;
        }
        if (this.state.step === 3) {
            await this.saveMapping();
            await this.doPreview();
            this.state.step = 4;
            return;
        }
        if (this.state.step === 4) {
            this.state.step = 5;
            return;
        }
        // For export mode, skip mapping/preview and jump straight to Run.
        if (this.state.step === 2 && !this.isImport()) {
            this.state.step = 5;
            return;
        }
        this.state.step += 1;
    }

    onBack() {
        if (this.state.step === 5 && !this.isImport()) {
            this.state.step = 2;
            return;
        }
        if (this.state.step > 1) this.state.step -= 1;
    }

    async onCancel() {
        // Reset the job to draft (keeps the file, wipes stats + lines)
        if (!this.state.snap.id) return;
        try {
            await this.orm.call(
                "mv.dataloader.job", "action_reset_to_draft",
                [[this.state.snap.id]], {},
            );
            await this.refreshSnap();
            this.state.step = 1;
            this.notif.add("Reset to draft.", { type: "info" });
        } catch (e) {
            this.state.error = this._msg(e);
        }
    }

    // ------------------------------------------------------------
    // Job persistence
    // ------------------------------------------------------------
    async ensureJob() {
        // Create a draft on first interaction if we don't already
        // have a persisted job.
        if (this.state.snap.id) return this.state.snap.id;
        const created = await this.orm.call(
            "mv.dataloader.job", "create",
            [{
                mode: this.state.snap.mode,
                model_id: this.state.snap.model_id || false,
            }],
            {},
        );
        this.state.snap.id = created;
        // Re-load snapshot so we have the generated name etc.
        await this.refreshSnap();
        return created;
    }

    async saveJob(patch) {
        // Merge the top-level snap changes and push them to the server.
        const id = await this.ensureJob();
        const vals = {};
        const s = this.state.snap;
        for (const k of ["mode","model_id","header_row","delimiter",
                         "match_field_id","match_by",
                         "on_error","export_domain"]) {
            if (patch[k] !== undefined) vals[k] = patch[k];
            else if (s[k] !== undefined && s[k] !== null) vals[k] = s[k];
        }
        // Never write id / name / stats
        delete vals.id;
        if (patch.export_field_ids !== undefined) {
            vals.export_field_ids = [[6, 0, patch.export_field_ids]];
        }
        try {
            await this.orm.call("mv.dataloader.job", "write", [[id], vals], {});
            await this.refreshSnap();
        } catch (e) {
            this.state.error = this._msg(e);
        }
    }

    async refreshSnap() {
        if (!this.state.snap.id) return;
        const fresh = await this.orm.call(
            "mv.dataloader.job", "dl_snapshot", [[this.state.snap.id]], {},
        );
        // Mutate the reactive object key-by-key rather than
        // replacing it wholesale. Replacing state.snap can
        // race with concurrent local mutations from click
        // handlers and can also confuse OWL's reactivity if
        // the new plain object arrives before the previous
        // render has flushed.
        for (const k of Object.keys(fresh)) {
            this.state.snap[k] = fresh[k];
        }
    }

    // ------------------------------------------------------------
    // Step 1 - Mode
    // ------------------------------------------------------------
    onSelectMode(mode) {
        if (this.state.snap.mode === mode) return;
        // Local change only; persisted on Next
        this.state.snap.mode = mode;
        // Clear match field if switching to insert/export
        if (["insert","export"].includes(mode)) {
            this.state.snap.match_field_id = false;
            this.state.snap.match_field_name = "";
        }
    }

    // ------------------------------------------------------------
    // Step 2 - Source
    // ------------------------------------------------------------
    filteredModels() {
        const q = (this.state.filterModel || "").toLowerCase().trim();
        if (!q) return this.state.models.slice(0, 300);
        return this.state.models.filter(
            (m) => (m.name || "").toLowerCase().includes(q)
                || (m.model || "").toLowerCase().includes(q),
        ).slice(0, 300);
    }

    async onSelectModel(m) {
        // 1. Update local state IMMEDIATELY so the checkmark
        //    + "Selected" chip render on the next tick, before
        //    the async round-trip to the server.
        this.state.snap.model_id = m.id;
        this.state.snap.model_name = m.model;
        this.state.snap.model_label = m.name;
        this.state.snap.match_field_id = false;
        this.state.snap.match_field_name = "";
        this.state.snap.export_field_ids = [];
        // 2. Load fields FIRST (fast) so step 3 dropdowns
        //    are ready even before the persistence returns.
        try {
            this.state.targetFields = await this.orm.call(
                "mv.dataloader.job", "dl_list_fields", [m.id], {},
            );
        } catch (e) {
            this.state.error = this._msg(e);
        }
        // 3. Persist to the server.
        try {
            await this.saveJob({ model_id: m.id });
            this.notif.add(`Model set: ${m.name}`, { type: "success" });
        } catch (e) {
            this.state.error = this._msg(e);
        }
    }

    async onClearModel() {
        // Clear the current model selection so the user can
        // switch to a different one. Wipes dependent state
        // (match field, export fields, targetFields cache)
        // both locally and on the server.
        this.state.snap.model_id = false;
        this.state.snap.model_name = "";
        this.state.snap.model_label = "";
        this.state.snap.match_field_id = false;
        this.state.snap.match_field_name = "";
        this.state.snap.export_field_ids = [];
        this.state.targetFields = [];
        if (this.state.snap.id) {
            try {
                await this.orm.call(
                    "mv.dataloader.job", "write",
                    [[this.state.snap.id], { model_id: false }], {},
                );
                await this.refreshSnap();
            } catch (e) {
                this.state.error = this._msg(e);
            }
        }
    }

    onDragOver(ev) { ev.preventDefault(); this.state.dragOver = true; }
    onDragLeave()  { this.state.dragOver = false; }
    async onDrop(ev) {
        ev.preventDefault();
        this.state.dragOver = false;
        const f = ev.dataTransfer && ev.dataTransfer.files
                && ev.dataTransfer.files[0];
        if (f) await this._uploadFile(f);
    }
    async onFilePick(ev) {
        const f = ev.target.files && ev.target.files[0];
        if (f) await this._uploadFile(f);
    }

    async _uploadFile(file) {
        this.state.uploading = true;
        this.state.error = "";
        try {
            const dataUrl = await new Promise((resolve, reject) => {
                const r = new FileReader();
                r.onload  = () => resolve(r.result);
                r.onerror = reject;
                r.readAsDataURL(file);
            });
            const b64 = String(dataUrl).split(",")[1] || "";
            const id = await this.ensureJob();
            await this.orm.call("mv.dataloader.job", "write", [[id], {
                source_file: b64,
                source_filename: file.name,
            }], {});
            await this.refreshSnap();
            this.notif.add(`Uploaded ${file.name}`, { type: "success" });
        } catch (e) {
            this.state.error = this._msg(e);
        } finally {
            this.state.uploading = false;
        }
    }

    onHeaderRowToggle(ev) { this.state.snap.header_row = !!ev.target.checked; }
    onDelimiterChange(ev) { this.state.snap.delimiter  = ev.target.value; }

    onMatchFieldChange(ev) {
        const fid = parseInt(ev.target.value, 10) || false;
        this.state.snap.match_field_id = fid;
        const f = this.state.targetFields.find((x) => x.id === fid);
        this.state.snap.match_field_name = f ? f.name : "";
    }
    onMatchByChange(ev) { this.state.snap.match_by = ev.target.value; }
    onOnErrorChange(ev) { this.state.snap.on_error = ev.target.value; }

    // Export-specific inputs
    onExportDomainInput(ev) { this.state.snap.export_domain = ev.target.value; }
    onToggleExportField(fid) {
        const ids = this.state.snap.export_field_ids.map((f) => f.id);
        const found = ids.indexOf(fid);
        let newIds;
        if (found >= 0) {
            newIds = ids.filter((x) => x !== fid);
        } else {
            newIds = [...ids, fid];
        }
        // Rebuild the display list locally
        this.state.snap.export_field_ids = this.state.targetFields
            .filter((f) => newIds.includes(f.id))
            .map((f) => ({ id: f.id, name: f.name, label: f.label }));
    }
    isExportFieldSelected(fid) {
        return this.state.snap.export_field_ids.some((f) => f.id === fid);
    }

    // ------------------------------------------------------------
    // Step 3 - Column mapping
    // ------------------------------------------------------------
    async doAutomap() {
        const id = await this.ensureJob();
        try {
            await this.orm.call(
                "mv.dataloader.job", "action_load_and_automap",
                [[id]], {},
            );
            await this.refreshSnap();
        } catch (e) {
            this.state.error = this._msg(e);
        }
    }

    filteredFieldsForPicker() {
        // Same list used in the mapping dropdowns.
        return this.state.targetFields;
    }

    onMappingFieldChange(mapId, ev) {
        const fid = parseInt(ev.target.value, 10) || false;
        const row = this.state.snap.mapping.find((m) => m.id === mapId);
        if (!row) return;
        const f = this.state.targetFields.find((x) => x.id === fid);
        row.target_field_id = fid;
        row.target_field_name = f ? f.name : "";
        row.target_ttype = f ? f.ttype : "";
        row.target_relation = f ? f.relation : "";
        row.skip = !fid;
    }
    onMappingSkipToggle(mapId, ev) {
        const row = this.state.snap.mapping.find((m) => m.id === mapId);
        if (!row) return;
        row.skip = !!ev.target.checked;
    }
    onMappingKeyInput(mapId, ev) {
        const row = this.state.snap.mapping.find((m) => m.id === mapId);
        if (!row) return;
        row.match_key_for_m2o = ev.target.value || "name";
    }
    countMapped() {
        return (this.state.snap.mapping || [])
            .filter((m) => !m.skip && m.target_field_id).length;
    }
    countUnmapped() {
        return (this.state.snap.mapping || [])
            .filter((m) => !m.skip && !m.target_field_id).length;
    }
    countSkipped() {
        return (this.state.snap.mapping || [])
            .filter((m) => m.skip).length;
    }

    async saveMapping() {
        const id = await this.ensureJob();
        try {
            await this.orm.call(
                "mv.dataloader.job", "dl_save_mapping",
                [[id], this.state.snap.mapping.map((m) => ({
                    id: m.id,
                    target_field_id: m.target_field_id || false,
                    match_key_for_m2o: m.match_key_for_m2o || "name",
                    skip: !!m.skip,
                }))],
                {},
            );
            await this.refreshSnap();
        } catch (e) {
            this.state.error = this._msg(e);
        }
    }

    // ------------------------------------------------------------
    // Step 4 - Preview
    // ------------------------------------------------------------
    async doPreview() {
        const id = await this.ensureJob();
        try {
            await this.orm.call(
                "mv.dataloader.job", "action_preview",
                [[id]], {},
            );
            await this.refreshSnap();
        } catch (e) {
            this.state.error = this._msg(e);
        }
    }

    previewOkCount() {
        return this.state.snap.lines.filter((l) => l.status === "preview").length;
    }
    previewErrCount() {
        return this.state.snap.lines.filter((l) => l.status === "error").length;
    }

    // ------------------------------------------------------------
    // Step 5 - Run
    // ------------------------------------------------------------
    async doExecute() {
        const id = await this.ensureJob();
        this.state.executing = true;
        this.state.error = "";
        try {
            await this.orm.call(
                "mv.dataloader.job", "action_execute",
                [[id]], {},
            );
            await this.refreshSnap();
            const s = this.state.snap;
            const msg = this.isImport()
                ? `Import ${s.state}: ${s.success_count} ok, ${s.error_count} errors, ${s.skip_count} skipped.`
                : `Export ${s.state}: ${s.total_rows} rows.`;
            this.notif.add(msg, {
                type: s.state === "done" ? "success" : "warning",
            });
        } catch (e) {
            this.state.error = this._msg(e);
        } finally {
            this.state.executing = false;
        }
    }

    downloadUrl(kind) {
        // kind = 'error_report' | 'exported_file' | 'source_file'
        const id = this.state.snap.id;
        if (!id) return "#";
        return `/web/content/mv.dataloader.job/${id}/${kind}?download=true`;
    }
}

// Register as a field widget bound to `id`. The form arch just
// drops <field name="id" widget="mv_dataloader_wizard"/> inside
// the sheet and this component takes over.
registry.category("fields").add("mv_dataloader_wizard", {
    component: MvDataloaderWizard,
    supportedTypes: ["integer"],
});
