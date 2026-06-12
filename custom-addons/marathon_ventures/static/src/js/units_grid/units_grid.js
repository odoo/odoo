/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const DAYPART_OPTIONS = [
    { value: "early_morning", label: "Early Morning", range: "6a - 9a" },
    { value: "day",           label: "Day",           range: "9a - 6p" },
    { value: "prime",         label: "Prime",         range: "6p - 12a" },
    { value: "late_fringe",   label: "Late Fringe",   range: "12a - 2a" },
    { value: "overnight",     label: "Overnight",     range: "2a - 6a" },
];

export class MvUnitsGrid extends Component {
    static template = "marathon_ventures.MvUnitsGrid";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.dayparts = DAYPART_OPTIONS;
        this._tempCounter = 0;
        this.state = useState({
            loaded: false,
            saving: false,
            payload: null,
            edits: { row_updates: [], row_creates: [], row_deletes: [], cell_updates: [] },
            dirty: false,
            justSaved: false,
            // Per-row context menu + delete-confirm dialog state.
            // openMenuRowId is the id (or 'tmp:N') of the row whose ⋯
            // menu is currently expanded; null if no menu open.
            openMenuRowId: null,
            // pendingDeleteRow holds the row object the user has clicked
            // "Delete" on but not yet confirmed; null if no dialog open.
            pendingDeleteRow: null,
            // pendingDiscard is true while the Discard-confirmation
            // dialog is open. Confirm -> reload the grid (dropping
            // edits); Cancel -> just close the dialog.
            pendingDiscard: false,
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
        this.state.payload = await this.orm.call("mv.deal", "load_units_grid", [[id]], {});
        console.log(this.state.payload);
        
        this.state.loaded = true;
        this.resetEdits();
    }

    resetEdits() {
        this.state.edits = {
            row_updates: [], row_creates: [], row_deletes: [],
            cell_updates: [],
            deal_update: {},   // Phase 12: holds units_start_date changes
        };
        this.state.dirty = false;
    }

    // Phase 12: deal-level start date changed -> snap to Monday,
    // queue the update, and locally regenerate the week columns so
    // the planner sees the new range before saving.
    onDealStartDateChange(ev) {
        const raw = ev.target.value || null;
        if (!raw) return;
        // Always snap to Monday of the picked week
        const snapped = this._snapToMondayIso(raw);
        this.state.edits.deal_update = { units_start_date: snapped };
        this.state.payload.deal.units_start_date = snapped;
        this._regenerateWeeksLocally(snapped);
        this._markDirty();
    }

    _snapToMondayIso(iso) {
        const d = new Date(iso + "T00:00:00");
        // JS getDay(): 0=Sun, 1=Mon, ..., 6=Sat
        while (d.getDay() !== 1) {
            d.setDate(d.getDate() - 1);
        }
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const dd = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${dd}`;
    }

    // ---- Broadcast-calendar helpers ----------------------------------
    // Mirror of phase12_deal_start_date.py's broadcast helpers. A
    // broadcast month starts on the Monday of the calendar week
    // containing the 1st of that calendar month. A broadcast quarter
    // starts at the broadcast month of (Jan / Apr / Jul / Oct) and
    // ends the day before the next broadcast quarter starts.
    //
    // Example: April 1, 2026 is a Wednesday, so broadcast Q2 2026
    // starts Monday March 30, 2026 and ends Sunday June 28, 2026.
    _broadcastMonthStart(year, month) {
        // month is 1..12 here (matches Python). JS Date uses 0..11
        // internally, but we keep the API 1..12 for clarity.
        const first = new Date(year, month - 1, 1);
        // JS getDay(): 0=Sun, 1=Mon, ..., 6=Sat
        // weekday-Mon0 = (getDay() + 6) % 7
        const weekdayMon0 = (first.getDay() + 6) % 7;
        first.setDate(first.getDate() - weekdayMon0);
        return first;
    }

    _broadcastQuarterBounds(d) {
        // Enumerate every quarter-start in a +/-1 year window, find the
        // bracket that contains `d`, return [start, end].
        const y = d.getFullYear();
        const cands = [];
        for (const yy of [y - 1, y, y + 1]) {
            for (const m of [1, 4, 7, 10]) {
                cands.push(this._broadcastMonthStart(yy, m));
            }
        }
        cands.sort((a, b) => a - b);
        for (let i = 0; i < cands.length; i++) {
            const s = cands[i];
            const next = i + 1 < cands.length ? cands[i + 1] : null;
            if (s <= d && (next === null || next > d)) {
                if (next === null) {
                    // Shouldn't happen with a +/-1y window.
                    const fb = new Date(s);
                    fb.setDate(fb.getDate() + 13 * 7 - 1);
                    return [s, fb];
                }
                const end = new Date(next);
                end.setDate(end.getDate() - 1);
                return [s, end];
            }
        }
        // Fallback
        const end = new Date(cands[1]);
        end.setDate(end.getDate() - 1);
        return [cands[0], end];
    }

    _regenerateWeeksLocally(startIso) {
        // JS mirror of mondays_for_start_date() - broadcast-calendar
        // edition. Includes only Mondays whose Mon..Sun week sits
        // entirely inside the broadcast quarter that contains the deal
        // start date.
        const d = new Date(startIso + "T00:00:00");
        // Snap to Monday of the picked week (defensive - usually
        // already snapped by _snapToMondayIso before this is called).
        const firstMonday = new Date(d);
        while (firstMonday.getDay() !== 1) {
            firstMonday.setDate(firstMonday.getDate() - 1);
        }
        const [, qEnd] = this._broadcastQuarterBounds(firstMonday);
        const weeks = [];
        const cur = new Date(firstMonday);
        while (true) {
            const weekSunday = new Date(cur);
            weekSunday.setDate(weekSunday.getDate() + 6);
            if (weekSunday > qEnd) break;
            const y = cur.getFullYear();
            const m = String(cur.getMonth() + 1).padStart(2, "0");
            const dd = String(cur.getDate()).padStart(2, "0");
            weeks.push(`${y}-${m}-${dd}`);
            cur.setDate(cur.getDate() + 7);
        }
        this.state.payload.weeks = weeks;
        // Resize each row's cells to match the new week count. We keep a
        // per-row `_masterCells` dict (week_iso -> cell object) that holds
        // EVERY cell the planner has ever seen (initial DB data + edits).
        // This is what lets the planner switch the Deal Start Date to a
        // previous quarter and back without losing edits or DB-backed
        // units that fell out of range temporarily.
        //
        // Cell objects are shared by reference between `row.cells` and
        // `row._masterCells`, so edits made via onCellInput /
        // applyBulkAllocation (which mutate `cell.units` in place)
        // automatically propagate into the master without any extra
        // bookkeeping.
        for (const row of this.state.payload.rows) {
            if (!row._masterCells) row._masterCells = {};
            // 1. Capture current cells into the master (any of them may be
            //    about to be pruned because their week left the range).
            for (const c of row.cells) {
                row._masterCells[c.week] = c;
            }
            // 2. Build the new visible cells list from the master, falling
            //    back to a fresh dashed cell for weeks we've never seen.
            row.cells = weeks.map((w) => row._masterCells[w] || {
                week: w, units: 0, state: "dashed", sched_id: false,
                cancelled_units: 0, cancelled_sched_ids: [],
            });
            // 3. Re-sync the master so any freshly-created dashed cells
            //    are tracked too (in case the planner edits them now).
            for (const c of row.cells) {
                row._masterCells[c.week] = c;
            }
        }
    }

    _markDirty() {
        this.state.dirty = true;
        this.state.justSaved = false;
    }

    // ---- Row management ---------------------------------------------
    addRow() {
        if (!this.state.payload) return;
        this._tempCounter += 1;
        const tempKey = String(this._tempCounter);
        const tempId = "tmp:" + tempKey;
        const weeks = this.state.payload.weeks || [];
        const dp = DAYPART_OPTIONS[0];
        const newRow = {
            id: tempId,
            _temp: tempKey,
            _is_new: true,
            daypart: dp.value,
            daypart_label: dp.label,
            time_range: dp.range,
            days_mask: [true, true, true, true, true, false, false],
            rate: 0,
            run_start: weeks[0] || null,
            run_end: weeks[weeks.length - 1] || null,
            cells: weeks.map((w) => ({
                week: w, units: 0, state: "dashed", sched_id: false,
            })),
            total_spots: 0,
            total_revenue: 0,
        };
        this.state.payload.rows.push(newRow);
        // Phase 12: run_start / run_end are no longer per-row from the
        // UI - the server auto-fills them from the deal-level
        // units_start_date when the row is created.
        this.state.edits.row_creates.push({
            temp_id: tempKey,
            daypart: newRow.daypart,
            time_range: newRow.time_range,
            days_mask: newRow.days_mask.slice(),
            rate: newRow.rate,
        });
        this._markDirty();
    }

    removeRow(row) {
        const rows = this.state.payload.rows;
        const idx = rows.indexOf(row);
        if (idx >= 0) rows.splice(idx, 1);
        if (row._is_new) {
            this.state.edits.row_creates = this.state.edits.row_creates.filter(
                (c) => c.temp_id !== row._temp,
            );
        } else {
            this.state.edits.row_deletes.push(row.id);
            this.state.edits.row_updates = this.state.edits.row_updates.filter(
                (u) => u.id !== row.id,
            );
            this.state.edits.cell_updates = this.state.edits.cell_updates.filter(
                (c) => c.row_id !== row.id,
            );
        }
        this._markDirty();
        this._recomputeTotals();
    }

    // ---- Context menu (⋯) + delete confirmation ---------------------
    toggleMenu(row) {
        if (this.state.openMenuRowId === row.id) {
            this.state.openMenuRowId = null;
        } else {
            this.state.openMenuRowId = row.id;
        }
    }

    closeMenu() {
        this.state.openMenuRowId = null;
    }

    requestDelete(row) {
        // Close the dropdown and open the confirm dialog.
        this.state.openMenuRowId = null;
        this.state.pendingDeleteRow = row;
    }

    confirmDelete() {
        const row = this.state.pendingDeleteRow;
        this.state.pendingDeleteRow = null;
        if (row) this.removeRow(row);
    }

    cancelDelete() {
        this.state.pendingDeleteRow = null;
    }

    // ---- Bulk allocation (per-row, two sections) -------------------
    _ensureBulk(row) {
        if (!row._bulk) {
            row._bulk = {
                // Section 1 (From / To / Units / Go). sec1_start defaults
                // to the deal start date when empty - see XML t-att-value.
                sec1_start: '', sec1_end: '', sec1_units: '',
                // Section 2 (To / Go) - cancels weeks after To.
                sec2_end: '', sec2_units: '',
            };
        }
        return row._bulk;
    }

    onBulkInputChange(row, key, ev) {
        this._ensureBulk(row)[key] = ev.target.value;
    }

    applyBulkAllocation(row, sectionKey) {
        const bulk = this._ensureBulk(row);
        const dealStart = this.state.payload && this.state.payload.deal &&
                         this.state.payload.deal.units_start_date;
        if (!dealStart) {
            alert("Please set the Deal Start Date first.");
            return;
        }
        const endIso = bulk[sectionKey + '_end'];
        if (!endIso) {
            alert("Please select an End Date.");
            return;
        }
        if (endIso < dealStart) {
            alert("End Date cannot be earlier than the Deal Start Date.");
            return;
        }
        const rowId = row._is_new ? "tmp:" + row._temp : row.id;
        const isSec2 = (sectionKey === 'sec2');

        // -------------------------------------------------------------
        // Section 2: only the End Date is needed. Every week AFTER the
        // picked End Date that has an ACTIVE schedule (units > 0 OR a
        // sched_id) is flagged as Cancelled. The active units count is
        // moved into the cell's `cancelled_units` accumulator and the
        // input is cleared so the planner can enter NEW active units
        // on top. Empty cells (no active data) are skipped entirely.
        // -------------------------------------------------------------
        if (isSec2) {
            let touched = 0;
            for (const cell of row.cells) {
                if (cell.week <= endIso) continue;
                const activeUnits = Number(cell.units) || 0;
                const hasActive = !!cell.sched_id || activeUnits > 0;
                if (!hasActive) continue;
                // Move active units into the cancelled bucket. The
                // editable input goes back to empty so the planner can
                // type a new active count on top of the cancelled one.
                cell.cancelled_units = (Number(cell.cancelled_units) || 0)
                                       + activeUnits;
                cell.units = 0;
                cell.state = 'dashed';
                cell.dirty = true;
                // The cancel-edit replaces any pending units write for
                // this (row, week). Any later typing will push a fresh
                // units edit alongside.
                const idx = this.state.edits.cell_updates.findIndex(
                    (e) => e.row_id === rowId && e.week === cell.week
                );
                if (idx !== -1) this.state.edits.cell_updates.splice(idx, 1);
                this.state.edits.cell_updates.push({
                    row_id: rowId, week: cell.week, cancelled: true,
                });
                touched += 1;
            }
            if (touched === 0) {
                alert(
                    "No active schedules fall after that End Date - " +
                    "nothing to cancel."
                );
                return;
            }
            this._markDirty();
            this._recomputeTotals();
            return;
        }

        // -------------------------------------------------------------
        // Section 1: From + To + Units + Go. From defaults to the deal
        // start date but is editable; we use the planner's chosen From
        // if set, else fall back to the deal start. Fill every cell in
        // [from..endIso] with the picked Units value.
        // -------------------------------------------------------------
        const sec1Start = bulk.sec1_start || dealStart;
        if (sec1Start > endIso) {
            alert("End Date cannot be earlier than From Date.");
            return;
        }
        const unitsRaw = bulk[sectionKey + '_units'];
        const units = parseFloat(unitsRaw);
        if (!Number.isFinite(units) || units <= 0) {
            alert("Please enter a positive units count.");
            return;
        }
        let touchedFill = 0;
        for (const cell of row.cells) {
            const inRange = (cell.week >= sec1Start && cell.week <= endIso);
            if (inRange) {
                cell.units = units;
                cell.dirty = true;
                cell.state = 'green';
                const existing = this.state.edits.cell_updates.find(
                    (e) => e.row_id === rowId && e.week === cell.week
                );
                if (existing) existing.units = units;
                else this.state.edits.cell_updates.push({
                    row_id: rowId, week: cell.week, units: units,
                });
                touchedFill += 1;
            }
        }
        if (touchedFill === 0) {
            alert("No visible week columns fall in that date range.");
            return;
        }
        // Clear the units input so the planner sees the action completed
        bulk[sectionKey + '_units'] = '';
        this._markDirty();
        this._recomputeTotals();
    }

    _findOrPushRowUpdate(row) {
        if (row._is_new) {
            return this.state.edits.row_creates.find((c) => c.temp_id === row._temp);
        }
        let upd = this.state.edits.row_updates.find((u) => u.id === row.id);
        if (!upd) {
            upd = { id: row.id };
            this.state.edits.row_updates.push(upd);
        }
        return upd;
    }

    onDaypartChange(row, ev) {
        const value = ev.target.value;
        const opt = DAYPART_OPTIONS.find((d) => d.value === value) || DAYPART_OPTIONS[0];
        row.daypart = opt.value;
        row.daypart_label = opt.label;
        row.time_range = opt.range;
        const upd = this._findOrPushRowUpdate(row);
        upd.daypart = opt.value;
        upd.time_range = opt.range;
        this._markDirty();
    }

    onRateChange(row, ev) {
        const n = parseFloat(ev.target.value);
        row.rate = Number.isFinite(n) ? n : 0;
        const upd = this._findOrPushRowUpdate(row);
        upd.rate = row.rate;
        this._markDirty();
        this._recomputeTotals();
    }

    onRunDateChange(row, which, ev) {
        const v = ev.target.value || null;
        if (which === "start") row.run_start = v;
        else                   row.run_end   = v;
        const upd = this._findOrPushRowUpdate(row);
        upd[which === "start" ? "run_start" : "run_end"] = v;
        this._markDirty();
    }

    onDayToggle(row, idx) {
        row.days_mask[idx] = !row.days_mask[idx];
        const upd = this._findOrPushRowUpdate(row);
        upd.days_mask = row.days_mask.slice();
        this._markDirty();
    }

    // ---- Cell editing ------------------------------------------------
    _findOrPushCellEdit(rowId, week) {
        const list = this.state.edits.cell_updates;
        const found = list.find((e) => e.row_id === rowId && e.week === week);
        if (found) return found;
        const created = { row_id: rowId, week: week, units: 0 };
        list.push(created);
        return created;
    }

    onCellInput(row, cell, ev) {
        const n = parseFloat(ev.target.value);
        const units = Number.isFinite(n) ? n : 0;
        cell.units = units;
        cell.dirty = true;
        const rowId = row._is_new ? "tmp:" + row._temp : row.id;
        this._findOrPushCellEdit(rowId, cell.week).units = units;
        this._markDirty();
        this._recomputeTotals();
    }

    _recomputeTotals() {
        let gs = 0, gr = 0, gc = 0;
        for (const row of this.state.payload.rows) {
            let s = 0, cancelled = 0;
            for (const c of row.cells) {
                s += Number(c.units) || 0;
                cancelled += Number(c.cancelled_units) || 0;
            }
            row.total_spots = s;
            row.total_revenue = s * (Number(row.rate) || 0);
            row.total_cancelled = cancelled;
            gs += s;
            gr += row.total_revenue;
            gc += cancelled;
        }
        this.state.payload.grand_total_spots = gs;
        this.state.payload.grand_total_revenue = gr;
        this.state.payload.grand_total_cancelled = gc;
    }

    async onSave() {
        if (this.state.saving) return;
        this.state.saving = true;
        try {
            const fresh = await this.orm.call(
                "mv.deal", "save_units_grid",
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
        // immediately. The actual reload happens in confirmDiscard().
        // If the planner has no unsaved changes, just no-op.
        if (!this.state.dirty) return;
        this.state.pendingDiscard = true;
    }

    confirmDiscard() {
        this.state.pendingDiscard = false;
        this.loadGrid();   // reloads from server, dropping local edits
    }

    cancelDiscard() {
        this.state.pendingDiscard = false;
    }

    // ---- Helpers used by the template -------------------------------
    cellClasses(row, cell) {
        const cls = ["mv-cell", "mv-cell--" + (cell.state || "dashed")];
        if (cell.dirty) cls.push("mv-cell--dirty");
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
}

registry.category("fields").add("mv_units_grid", {
    component: MvUnitsGrid,
    supportedTypes: ["integer"],
});
