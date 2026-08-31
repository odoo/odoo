/** @odoo-module **/

/* Capping Grid OWL widget - sister of MvUnitsGrid for the Deal form's
 * "Capping Report" tab. Each cell shows effective/booked + cap %.
 * Editable cap % per cell, plus bulk actions: Set cap %, Ghost all,
 * Clear selection on the rows checked via the row checkbox.
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MvCappingGrid extends Component {
    static template = "marathon_ventures.MvCappingGrid";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loaded: false,
            saving: false,
            payload: null,
            edits: { cell_updates: [], row_cap_pct: [], row_ghost_all: [] },
            dirty: false,
            justSaved: false,
            selected: {},  // {row_id: true}
            // True while the Discard-confirmation dialog is open.
            // Confirm -> reload the grid; Cancel -> close the dialog.
            pendingDiscard: false,
            // Bulk cap picklist dialog state. When `pendingBulkCap`
            // is true the dialog is open; `pendingBulkCapValue` holds
            // the cap Selection value the planner has chosen.
            // pendingBulkCapStart/End restrict the write to weeks
            // whose Monday falls in [start, end]. Defaults come from
            // the first / last week columns rendered in the grid so
            // the planner sees the natural range up front.
            pendingBulkCap: false,
            pendingBulkCapValue: "uncapped",
            pendingBulkCapStart: "",
            pendingBulkCapEnd: "",
        });
        onWillStart(this.loadGrid.bind(this));
        onWillUpdateProps((nextProps) => {
            const oldId = this.props.record && this.props.record.resId;
            const newId = nextProps.record && nextProps.record.resId;
            if (newId && newId !== oldId) this.loadGrid(newId);
        });
    }

    get dealId() { return this.props.record && this.props.record.resId; }

    async loadGrid(idOverride) {
        const id = idOverride || this.dealId;
        if (!id) { this.state.loaded = true; return; }
        this.state.payload = await this.orm.call("mv.deal", "load_capping_grid", [[id]], {});
        this.state.loaded = true;
        this.resetEdits();
        this.state.selected = {};
    }

    resetEdits() {
        this.state.edits = { cell_updates: [], row_cap_pct: [], row_ghost_all: [] };
        this.state.dirty = false;
    }

    _markDirty() {
        this.state.dirty = true;
        this.state.justSaved = false;
    }

    // ---- Cell-level editing ----------------------------------------
    // Static fallback if the backend payload pre-dates the cap_options
    // key (e.g., the user is on a cached load_capping_grid response).
    static FALLBACK_CAP_OPTIONS = [
        { value: 'uncapped', label: 'Uncapped', pct: 100 },
        { value: 'v_80',     label: '80%',     pct: 80 },
        { value: 'v_50',     label: '50%',     pct: 50 },
        { value: 'v_0',      label: '0%',      pct: 0 },
        { value: 'ghost',    label: 'Ghost',   pct: 0 },
    ];

    get capOptions() {
        const fromPayload = this.state.payload && this.state.payload.cap_options;
        if (Array.isArray(fromPayload) && fromPayload.length) {
            return fromPayload;
        }
        return MvCappingGrid.FALLBACK_CAP_OPTIONS;
    }

    // Look up an option by value. Returns {value, label, pct} or a
    // sane default for unknown values.
    _capOptionFor(value) {
        return this.capOptions.find((o) => o.value === value)
            || { value: 'uncapped', label: 'Uncapped', pct: 100 };
    }

    onCapSelect(row, cell, ev) {
        if (cell.state === 'hatched' || cell.state === 'dashed') return;
        const newCap = ev.target.value;
        const opt = this._capOptionFor(newCap);
        const n = opt.pct;
        cell.cap = newCap;
        cell.cap_pct = n;
        cell.units_effective = Math.round((cell.units_booked || 0) * n / 100);
        // Visual state follows cap percent (and cap value 'ghost' maps
        // to gray even though pct=0 would also be gray).
        if (newCap === 'ghost' || n === 0) cell.state = 'gray';
        else if (n >= 100) cell.state = 'green';
        else cell.state = 'amber';
        cell.dirty = true;
        // Use sched_id as the lookup key on the server. We also send
        // row_id + week as a fallback in case sched_id is missing.
        // Send BOTH cap (Selection) and cap_pct (Integer) so the
        // backend writes both fields on the schedule and the existing
        // effective_spots compute can recompute correctly.
        const list = this.state.edits.cell_updates;
        const found = list.find((e) => e.sched_id === cell.sched_id);
        if (found) {
            found.cap = newCap;
            found.cap_pct = n;
        } else {
            list.push({
                sched_id: cell.sched_id,
                row_id: row.id,
                week: cell.week,
                cap: newCap,
                cap_pct: n,
            });
        }
        this._markDirty();
        this._recomputeTotals();
    }

    // ---- Row selection + bulk actions ------------------------------
    toggleRow(rowId, ev) {
        if (ev && ev.target) {
            this.state.selected[rowId] = !!ev.target.checked;
        } else {
            this.state.selected[rowId] = !this.state.selected[rowId];
        }
    }

    toggleAll(ev) {
        const v = !!(ev && ev.target && ev.target.checked);
        for (const row of (this.state.payload.rows || [])) {
            this.state.selected[row.id] = v;
        }
    }

    get selectedRowIds() {
        // Phase 15: row.id is now a signature string like
        // '1111100|100.00|v_06_00a|v_09_00a|0' (not a deal_line
        // integer id). parseInt() on that returns 1111100, which
        // silently corrupts every bulk-action payload (Set cap %,
        // Ghost all, LTC, ...). Return the object keys verbatim.
        return Object.keys(this.state.selected)
            .filter((k) => this.state.selected[k]);
    }

    clearSelection() {
        this.state.selected = {};
    }

    // Opens the cap picklist dialog. The actual write happens in
    // confirmBulkCap() after the planner picks an option.
    setBulkCapPct() {
        if (!this.selectedRowIds.length) return;
        this.state.pendingBulkCap = true;
        // Default selection: keep the last picked value, else uncapped.
        if (!this.state.pendingBulkCapValue) {
            this.state.pendingBulkCapValue = "uncapped";
        }
        // Default date range = first / last week currently rendered
        // in the grid. Weeks are ISO Mondays; the end date on-screen
        // is Sunday of the last week (last Monday + 6d).
        const weeks = (this.state.payload && this.state.payload.weeks) || [];
        if (weeks.length) {
            this.state.pendingBulkCapStart = weeks[0];
            // Push end to the Sunday of the last week so the input
            // matches the grid's visible span.
            try {
                const lastMon = new Date(weeks[weeks.length - 1] + "T00:00:00");
                lastMon.setDate(lastMon.getDate() + 6);
                const y = lastMon.getFullYear();
                const m = String(lastMon.getMonth() + 1).padStart(2, "0");
                const dd = String(lastMon.getDate()).padStart(2, "0");
                this.state.pendingBulkCapEnd = `${y}-${m}-${dd}`;
            } catch (e) {
                this.state.pendingBulkCapEnd = weeks[weeks.length - 1];
            }
        }
    }

    onBulkCapSelect(ev) {
        this.state.pendingBulkCapValue = ev.target.value;
    }
    onBulkCapStartInput(ev) { this.state.pendingBulkCapStart = ev.target.value || ""; }
    onBulkCapEndInput(ev)   { this.state.pendingBulkCapEnd   = ev.target.value || ""; }

    cancelBulkCap() {
        this.state.pendingBulkCap = false;
    }

    // Confirm = apply the picked cap to every selected row. We keep
    // the same logic the old prompt path used - just sourced from the
    // dropdown instead of a free-form numeric prompt.
    async confirmBulkCap() {
        const ids = this.selectedRowIds;
        this.state.pendingBulkCap = false;
        if (!ids.length) return;
        const capValue = this.state.pendingBulkCapValue || "uncapped";
        const opt = this._capOptionFor(capValue);
        let pct = opt.pct;
        if (!Number.isFinite(pct)) pct = 100;
        pct = Math.max(0, Math.min(100, pct));
        // Optional date range from the modal. If either bound is
        // blank we treat that side as unbounded.
        const start = (this.state.pendingBulkCapStart || "").trim();
        const end   = (this.state.pendingBulkCapEnd   || "").trim();
        if (start && end && end < start) {
            alert("End Date must be on or after Start Date.");
            return;
        }
        // A week (Monday) intersects [start, end] if its Sunday
        // (Monday + 6d) is >= start AND its Monday is <= end.
        const inRange = (weekIso) => {
            if (!weekIso) return false;
            if (start) {
                // week's Sunday must be >= start
                let sun;
                try {
                    const d = new Date(weekIso + "T00:00:00");
                    d.setDate(d.getDate() + 6);
                    sun = d.toISOString().slice(0, 10);
                } catch (e) { sun = weekIso; }
                if (sun < start) return false;
            }
            if (end && weekIso > end) return false;
            return true;
        };
        for (const rid of ids) {
            // Send BOTH pct and the picklist selection. Without the
            // explicit `cap`, ghost (pct=0) and v_0 (pct=0) collide
            // and the backend would reverse-map both to 'v_0' via
            // _cap_pct_to_value. Include the date range so the
            // backend only touches schedules within it.
            this.state.edits.row_cap_pct.push({
                row_id: rid, cap_pct: pct, cap: capValue,
                start_date: start || null,
                end_date: end || null,
            });
            const row = this.state.payload.rows.find((r) => r.id === rid);
            if (row) {
                for (const c of row.cells) {
                    if (c.state === 'hatched' || c.state === 'dashed') continue;
                    if (!inRange(c.week)) continue;   // out-of-range cell
                    c.cap_pct = pct;
                    c.cap = capValue;
                    c.units_effective = Math.round((c.units_booked || 0) * pct / 100 * 100) / 100;
                    if (capValue === 'ghost') c.state = 'gray';
                    else if (pct >= 100) c.state = 'green';
                    else if (pct === 0) c.state = 'gray';
                    else c.state = 'amber';
                    c.dirty = true;
                }
            }
        }
        this._markDirty();
        this._recomputeTotals();
    }

    ghostAllSelected() {
        const ids = this.selectedRowIds;
        if (!ids.length) return;
        for (const rid of ids) {
            this.state.edits.row_ghost_all.push(rid);
            const row = this.state.payload.rows.find((r) => r.id === rid);
            if (row) {
                for (const c of row.cells) {
                    if (c.state === 'hatched' || c.state === 'dashed') continue;
                    c.cap_pct = 0;
                    c.cap = 'ghost';
                    c.units_effective = 0;
                    c.state = 'gray';
                    c.dirty = true;
                }
            }
        }
        this._markDirty();
        this._recomputeTotals();
    }

    _recomputeTotals() {
        let gb = 0, ge = 0, gr = 0;
        for (const row of this.state.payload.rows) {
            let rb = 0, re = 0;
            for (const c of row.cells) {
                if (c.state === 'hatched' || c.state === 'dashed') continue;
                rb += Number(c.units_booked) || 0;
                re += Number(c.units_effective) || 0;
            }
            row.row_booked = rb;
            row.row_effective = re;
            row.row_revenue = re * (Number(row.rate) || 0);
            gb += rb; ge += re; gr += row.row_revenue;
        }
        this.state.payload.grand_booked = gb;
        this.state.payload.grand_effective = ge;
        this.state.payload.grand_revenue = gr;
    }

    async onSave() {
        if (this.state.saving) return;
        this.state.saving = true;
        try {
            const fresh = await this.orm.call(
                "mv.deal", "save_capping_grid",
                [[this.dealId], this.state.edits], {},
            );
            this.state.payload = fresh;
            this.resetEdits();
            this.state.justSaved = true;
            setTimeout(() => { this.state.justSaved = false; }, 3000);
        } finally {
            this.state.saving = false;
        }
    }

    onDiscard() {
        // Open the confirmation dialog instead of dropping edits
        // immediately. If there's nothing to discard, no-op.
        if (!this.state.dirty) return;
        this.state.pendingDiscard = true;
    }

    confirmDiscard() {
        this.state.pendingDiscard = false;
        this.loadGrid();   // reloads from server, dumping local edits
    }

    cancelDiscard() {
        this.state.pendingDiscard = false;
    }

    cellClasses(cell) {
        const cls = ["mv-cap-cell", "mv-cap-cell--" + (cell.state || "dashed")];
        if (cell.dirty) cls.push("mv-cap-cell--dirty");
        return cls.join(" ");
    }

    fmtCurrency(amount) {
        if (!this.state.payload) return amount;
        const cur = this.state.payload.currency;
        const sym = cur.symbol || "$";
        const n = Number(amount || 0).toLocaleString(undefined, {
            minimumFractionDigits: 0, maximumFractionDigits: 0,
        });
        return cur.position === "after" ? n + sym : sym + n;
    }

    fmtWeekShort(iso) {
        if (!iso) return "";
        const d = new Date(iso + "T00:00:00");
        return (d.getMonth() + 1) + "/" + d.getDate();
    }

    capLabel(cell) {
        if (cell.state === 'hatched' || cell.state === 'dashed') return '';
        if (cell.cap_pct === 0) return 'Ghost';
        return cell.cap_pct + '%';
    }

    get hasSelection() {
        return this.selectedRowIds.length > 0;
    }
}

registry.category("fields").add("mv_capping_grid", {
    component: MvCappingGrid,
    supportedTypes: ["integer"],
});
