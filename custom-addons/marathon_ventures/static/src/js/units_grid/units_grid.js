/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const DAYPART_OPTIONS = [
    { value: "early_morning", label: "Early Morning", range: "6a - 9a",
      start: "v_06_00a", end: "v_09_00a" },
    { value: "day",           label: "Day",           range: "9a - 6p",
      start: "v_09_00a", end: "v_06_00p" },
    { value: "prime",         label: "Prime",         range: "6p - 12a",
      start: "v_06_00p", end: "v_12_00a" },
    { value: "late_fringe",   label: "Late Fringe",   range: "12a - 3a",
      start: "v_12_00a", end: "v_03_00a" },
    { value: "overnight",     label: "Overnight",     range: "3a - 6a",
      start: "v_03_00a", end: "v_06_00a" },
    // Selected automatically when the planner enters a (start, end) pair
    // that doesn't match any of the standard dayparts above.
    { value: "custom",        label: "Custom",        range: "",
      start: null,        end: null },
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
            // LTC dialog state. pendingLtcRow holds the row object;
            // pendingLtcDate is the planner-typed date inside the LTC
            // week. Both clear when the dialog closes.
            pendingLtcRow: null,
            pendingLtcDate: "",
            // Multi-row selection state. `selected` is keyed by row.id
            // (only real rows, not LTC previews). bulkAction tracks
            // which bulk modal is open: "" (none), "ltc", "maxday",
            // or "hiatus". bulkLtcDate / bulkMaxDay / bulkHiatusStart
            // / bulkHiatusEnd back the inputs in those modals.
            selected: {},
            bulkAction: "",
            bulkLtcDate: "",
            bulkMaxDay: "",
            bulkHiatusStart: "",
            bulkHiatusEnd: "",
            // Update Rate bulk action inputs
            bulkRateStart: "",
            bulkRateEnd: "",
            bulkRateValue: "",
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
        // Program-specific dayparts: when the deal's program has any
        // configured, use them for the daypart dropdown. Otherwise
        // fall back to the hardcoded DAYPART_OPTIONS. We always
        // keep the 'custom' entry as a final fallback so a planner
        // can still enter a free-form time pair.
        const progDp = (this.state.payload && this.state.payload.program_dayparts) || [];
        if (progDp.length) {
            const customFallback = DAYPART_OPTIONS.find((d) => d.value === "custom");
            this.dayparts = customFallback ? [...progDp, customFallback] : [...progDp];
        } else {
            this.dayparts = DAYPART_OPTIONS;
        }
        // Prime the per-row bulk-allocation block so the "To" input
        // renders its pre-filled last-day-of-quarter default on first
        // paint. Without this, _ensureBulk only runs when the planner
        // interacts with the section, and the "To" input starts empty.
        for (const row of (this.state.payload.rows || [])) {
            this._ensureBulk(row);
        }
        this.state.loaded = true;
        this.resetEdits();
    }

    resetEdits() {
        this.state.edits = {
            row_updates: [], row_creates: [], row_deletes: [],
            cell_updates: [],
            deal_update: {},   // Phase 12: holds units_start_date changes
            ltc_ops: [],       // Staged Last-To-Cancel operations
            hiatus_ops: [],    // Staged Hiatus operations (bulk action)
            rate_ops: [],      // Staged Update-Rate operations (bulk action)
        };
        this.state.dirty = false;
        // Drop any selection + bulk-bar state too - the rows from the
        // freshly-loaded payload may have different ids.
        this.state.selected = {};
        this.state.bulkAction = "";
        this.state.bulkLtcDate = "";
        this.state.bulkMaxDay = "";
        this.state.bulkHiatusStart = "";
        this.state.bulkHiatusEnd = "";
        this.state.bulkRateStart = "";
        this.state.bulkRateEnd = "";
        this.state.bulkRateValue = "";
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
            start_time: dp.start,
            end_time: dp.end,
            cells: weeks.map((w) => ({
                week: w, units: 0, state: "dashed", sched_id: false,
            })),
            total_spots: 0,
            total_revenue: 0,
        };
        // Prime the bulk block on the fresh row so its "To" input
        // renders the pre-filled last-day-of-quarter on the first
        // paint (same as existing rows do via loadGrid's priming).
        this._ensureBulk(newRow);
        this.state.payload.rows.push(newRow);
        // Phase 12: run_start / run_end are no longer per-row from the
        // UI - the server auto-fills them from the deal-level
        // units_start_date when the row is created.
        // Send every signature-defining field so the backend can
        // build the schedule signature (days + rate + start_time +
        // end_time + max_per_day) when the first cell is filled.
        // Missing start_time/end_time here would materialize
        // schedules with empty times.
        this.state.edits.row_creates.push({
            temp_id: tempKey,
            daypart: newRow.daypart,
            time_range: newRow.time_range,
            days_mask: newRow.days_mask.slice(),
            rate: newRow.rate,
            start_time: newRow.start_time || false,
            end_time: newRow.end_time || false,
            max_per_day: newRow.max_per_day || 0,
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
        if (row._is_ltc_preview) {
            this.closeMenu();
            alert("This is a preview row. Save the LTC first or click Discard.");
            return;
        }
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
                // sec1_end defaults to the Sunday of the LAST week
                // currently rendered in the grid (i.e. the last date of
                // the broadcast quarter the deal spans) so a planner who
                // just clicks Go covers the whole visible range.
                sec1_start: '', sec1_end: this._gridEndDateIso(), sec1_units: '',
                // Section 2 (To / Go) - cancels weeks after To.
                sec2_end: '', sec2_units: '',
            };
        }
        return row._bulk;
    }

    // ISO of the LAST week header shown in the current grid.
    // Matches the last column's date (Monday-of-week) so the pre-
    // filled "To" input lines up with what the planner sees in the
    // week column headers. Returns '' when the payload has no
    // weeks yet (e.g. brand-new deal with no schedules).
    _gridEndDateIso() {
        const weeks = this.state.payload && this.state.payload.weeks;
        if (!weeks || !weeks.length) return '';
        return weeks[weeks.length - 1];
    }

    onBulkInputChange(row, key, ev) {
        this._ensureBulk(row)[key] = ev.target.value;
    }

    applyBulkAllocation(row, sectionKey) {
        if (row._is_ltc_preview) {
            alert("This is a preview row. Save the LTC first to make further edits.");
            return;
        }
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
        if (row._is_ltc_preview) { ev.target.value = row.daypart; return; }
        const value = ev.target.value;
        // Look up in this.dayparts (which may include program-defined
        // dayparts like "prog_5" alongside the hardcoded DAYPART_OPTIONS)
        // before falling back to the hardcoded list.
        const opt = (this.dayparts || DAYPART_OPTIONS).find((d) => d.value === value)
            || DAYPART_OPTIONS.find((d) => d.value === value)
            || DAYPART_OPTIONS[0];
        // Debug: open DevTools -> Console. When picking a daypart,
        // you should see the picked option including start/end and
        // days_bits (for program dayparts). If days_bits is missing
        // the payload isn't shipping it - restart Odoo + upgrade.
        // eslint-disable-next-line no-console
        console.log("[UnitsGrid] daypart picked:", value,
            "-> opt:", opt,
            "row.days_mask before:", row.days_mask && row.days_mask.slice());
        row.daypart = opt.value;
        row.daypart_label = opt.label;
        row.time_range = opt.range;
        const upd = this._findOrPushRowUpdate(row);
        upd.daypart = opt.value;
        upd.time_range = opt.range;
        // For predefined dayparts, snap start_time / end_time to the
        // standard range so the time dropdowns stay in sync. For
        // 'custom', leave whatever the planner already chose.
        if (opt.start && opt.end) {
            row.start_time = opt.start;
            row.end_time   = opt.end;
            upd.start_time = opt.start;
            upd.end_time   = opt.end;
        }
        // Program-defined dayparts carry a days_bits string (e.g.
        // "1111100" for M-F). When the planner picks one, auto-fill
        // the row's day checkboxes so the Days Allowed matches the
        // daypart's configured days. The planner can still edit them
        // afterwards - we just prime the checkboxes.
        if (typeof opt.days_bits === "string" && /^[01]{7}$/.test(opt.days_bits)) {
            const mask = opt.days_bits.split("").map((c) => c === "1");
            row.days_mask = mask;
            upd.days_mask = mask.slice();
        }
        this._markDirty();
    }

    // Triggered by either the Start Time or End Time <select> in a
    // row. Pushes the new value into the queued row_update and then
    // checks whether the resulting (start, end) pair still matches a
    // predefined daypart - if not, the row's daypart switches to
    // 'custom' automatically.
    onTimeChange(row, which, ev) {
        if (row._is_ltc_preview) {
            ev.target.value = (which === "start" ? row.start_time : row.end_time) || "";
            return;
        }
        const v = ev.target.value || null;
        if (which === "start") row.start_time = v;
        else                   row.end_time   = v;
        const upd = this._findOrPushRowUpdate(row);
        upd[which === "start" ? "start_time" : "end_time"] = v;

        // Auto-detect daypart from the new (start, end) pair using the
        // containment rules (mirrors phase10._guess_daypart_with_program):
        //   1. Exact match wins outright.
        //   2. Otherwise, the smallest-span daypart whose interval
        //      fully contains the schedule's [start, end] wins.
        //   3. If nothing contains, fall back to "custom".
        // Searches this.dayparts (program dayparts + hardcoded 'custom')
        // when the program has custom dayparts; otherwise falls back to
        // DAYPART_OPTIONS' hardcoded list.
        const candidates = (this.dayparts && this.dayparts.length)
            ? this.dayparts : DAYPART_OPTIONS;
        const newDp = this._resolveDaypartByContainment(
            candidates, row.start_time, row.end_time,
        );
        // Diagnostic - open DevTools > Console. If you don't see this
        // log line when editing a time, the browser is running the
        // OLD bundle - hard-refresh (Ctrl+Shift+R).
        // eslint-disable-next-line no-console
        console.log(
            "[UnitsGrid] onTimeChange containment:",
            row.start_time, "->", row.end_time,
            "picked:", newDp && newDp.value, newDp && newDp.label,
            "candidates:", candidates.map((d) => d.value),
        );
        if (newDp && row.daypart !== newDp.value) {
            row.daypart = newDp.value;
            row.daypart_label = newDp.label;
            row.time_range = newDp.range;
            upd.daypart = newDp.value;
            upd.time_range = newDp.range;
        }
        this._markDirty();
    }

    // ---- Daypart containment helpers (mirror the backend logic) ------
    // Turn 'v_HH_MMa' / 'v_HH_MMp' into minutes since midnight (0..1439).
    // Odoo convention: 12A = midnight, 12P = noon.
    _timeToMinutes(t) {
        if (!t || typeof t !== "string" || !t.startsWith("v_")) return null;
        const body = t.slice(2);           // "HH_MMa" or "HH_MMp"
        if (body.length < 6) return null;
        const hh = parseInt(body.slice(0, 2), 10);
        const mm = parseInt(body.slice(3, 5), 10);
        const suf = body[5];
        if (!Number.isFinite(hh) || !Number.isFinite(mm)) return null;
        if (suf === "a") return hh === 12 ? mm : hh * 60 + mm;
        if (suf === "p") return hh === 12 ? 12 * 60 + mm : (hh + 12) * 60 + mm;
        return null;
    }

    // Total minutes an interval spans on a 24h clock. start == end -> 1440
    // (ROS 6a-6a). end < start -> wraparound (Prime 6p-12a).
    _dpSpan(startMin, endMin) {
        if (startMin === null || endMin === null) return null;
        if (endMin === startMin) return 1440;
        if (endMin > startMin) return endMin - startMin;
        return (1440 - startMin) + endMin;
    }

    _offsetFrom(startMin, atMin) {
        if (startMin === null || atMin === null) return null;
        if (atMin >= startMin) return atMin - startMin;
        return (1440 - startMin) + atMin;
    }

    // True when the schedule interval fits fully inside the daypart interval.
    _daypartContainsSchedule(dpStart, dpEnd, schStart, schEnd) {
        const ds = this._timeToMinutes(dpStart);
        const de = this._timeToMinutes(dpEnd);
        const ss = this._timeToMinutes(schStart);
        const se = this._timeToMinutes(schEnd);
        if ([ds, de, ss, se].some((x) => x === null)) return false;
        const dpSpan  = this._dpSpan(ds, de);
        const schSpan = this._dpSpan(ss, se);
        const off     = this._offsetFrom(ds, ss);
        if (dpSpan === null || schSpan === null || off === null) return false;
        return off + schSpan <= dpSpan;
    }

    // Pick the best daypart for a given (start, end) from the candidates:
    //   1. Exact match wins.
    //   2. Smallest containing daypart wins.
    //   3. Otherwise the "custom" entry (from candidates or DAYPART_OPTIONS).
    _resolveDaypartByContainment(candidates, schStart, schEnd) {
        if (!schStart || !schEnd) {
            return candidates.find((d) => d.value === "custom")
                || DAYPART_OPTIONS.find((d) => d.value === "custom");
        }
        let exact = null;
        const contained = [];   // {span, dp}
        for (const dp of candidates) {
            if (!dp || dp.value === "custom") continue;
            if (!dp.start || !dp.end) continue;
            if (dp.start === schStart && dp.end === schEnd) {
                exact = dp;
                break;
            }
            if (this._daypartContainsSchedule(dp.start, dp.end, schStart, schEnd)) {
                const ds = this._timeToMinutes(dp.start);
                const de = this._timeToMinutes(dp.end);
                const span = this._dpSpan(ds, de) || 1440;
                contained.push({ span, dp });
            }
        }
        if (exact) return exact;
        if (contained.length) {
            contained.sort((a, b) => a.span - b.span);
            return contained[0].dp;
        }
        return candidates.find((d) => d.value === "custom")
            || DAYPART_OPTIONS.find((d) => d.value === "custom");
    }

    onMaxPerDayChange(row, ev) {
        if (row._is_ltc_preview) {
            ev.target.value = row.max_per_day || 0;
            return;
        }
        const n = parseInt(ev.target.value, 10);
        row.max_per_day = Number.isFinite(n) && n >= 0 ? n : 0;
        const upd = this._findOrPushRowUpdate(row);
        upd.max_per_day = row.max_per_day;
        this._markDirty();
    }

    onRateChange(row, ev) {
        if (row._is_ltc_preview) { ev.target.value = row.rate || 0; return; }
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
        if (row._is_ltc_preview) return;
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
        if (row._is_ltc_preview) {
            // Preview rows are pure UI - reject edits; the planner
            // can adjust the real split row after Save.
            ev.target.value = cell.units || "";
            return;
        }
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

    // ---- LTC (Last To Cancel) ---------------------------------------
    // Two entry points: the row's ⋯ menu (requestLtc -> confirmLtc) and
    // Section 2 of the bulk strip (applyLtcFromSection2). Both call
    // _dispatchApplyLtc which hits the backend apply_ltc RPC.
    requestLtc(row) {
        this.closeMenu();
        this.state.pendingLtcRow = row;
        const dealStart = this.state.payload
            && this.state.payload.deal
            && this.state.payload.deal.units_start_date;
        this.state.pendingLtcDate = dealStart || "";
    }

    onLtcDateInput(ev) {
        this.state.pendingLtcDate = ev.target.value || "";
    }

    cancelLtc() {
        this.state.pendingLtcRow = null;
        this.state.pendingLtcDate = "";
    }

    confirmLtc() {
        const row = this.state.pendingLtcRow;
        const dateIso = this.state.pendingLtcDate;
        if (!row || !dateIso) {
            alert("Please pick an LTC date.");
            return;
        }
        this._stageLtc(row, dateIso);
        this.state.pendingLtcRow = null;
        this.state.pendingLtcDate = "";
    }

    applyLtcFromSection2(row) {
        if (row._is_ltc_preview) {
            alert("This is a preview row from an unsaved LTC. Save first, then apply another LTC.");
            return;
        }
        const bulk = this._ensureBulk(row);
        const dateIso = bulk.sec2_end;
        if (!dateIso) {
            alert("Please pick a date in Section 2 before clicking Go.");
            return;
        }
        this._stageLtc(row, dateIso);
        bulk.sec2_end = "";
    }

    // ---- Multi-row selection + bulk LTC -----------------------------
    toggleRow(rowId, ev) {
        const v = !!(ev && ev.target && ev.target.checked);
        this.state.selected[rowId] = v;
    }

    toggleAll(ev) {
        const v = !!(ev && ev.target && ev.target.checked);
        for (const row of (this.state.payload.rows || [])) {
            // Don't select preview rows - they're not real Deal Lines.
            if (row._is_ltc_preview) continue;
            this.state.selected[row.id] = v;
        }
    }

    get selectedRowIds() {
        return Object.keys(this.state.selected)
            .filter((k) => this.state.selected[k]);
    }

    get hasSelection() {
        return this.selectedRowIds.length > 0;
    }

    clearSelection() {
        this.state.selected = {};
    }

    onBulkLtcDateInput(ev) {
        this.state.bulkLtcDate = ev.target.value || "";
    }

    // ---- Bulk Action dropdown (LTC / Max/Day) ---------------------
    onBulkActionSelect(ev) {
        const value = (ev.target.value || "").trim();
        ev.target.value = "";   // reset the <select> so the placeholder shows again
        if (!this.selectedRowIds.length) {
            alert("No rows selected.");
            return;
        }
        if (value === "ltc") {
            this.state.bulkAction = "ltc";
            if (!this.state.bulkLtcDate) {
                const dealStart = this.state.payload
                    && this.state.payload.deal
                    && this.state.payload.deal.units_start_date;
                this.state.bulkLtcDate = dealStart || "";
            }
        } else if (value === "maxday") {
            this.state.bulkAction = "maxday";
            this.state.bulkMaxDay = "";
        } else if (value === "hiatus") {
            this.state.bulkAction = "hiatus";
            // Pre-populate the range with the deal's current
            // broadcast-quarter bounds so the planner has a sensible
            // starting range they can shrink to the actual hiatus.
            const dealStart = this._isoDate(new Date())
            
            const now = new Date();
            const end = new Date(now.getTime() + 7 * 86400000);
            this.state.bulkHiatusStart = this._isoDate(now);
            this.state.bulkHiatusEnd   = this._isoDate(end);
        } else if (value === "rate") {
            this.state.bulkAction = "rate";
            // Default the date range to the full grid so a planner
            // who just wants to change every week's rate doesn't
            // have to pick dates. They can narrow it after.
            const weeks = (this.state.payload && this.state.payload.weeks) || [];
            if (weeks.length) {
                this.state.bulkRateStart = weeks[0];
                try {
                    const lastMon = new Date(weeks[weeks.length - 1] + "T00:00:00");
                    lastMon.setDate(lastMon.getDate() + 6);
                    this.state.bulkRateEnd = this._isoDate(lastMon);
                } catch (e) {
                    this.state.bulkRateEnd = weeks[weeks.length - 1];
                }
            }
            this.state.bulkRateValue = "";
        }
    }

    _isoDate(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const dd = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${dd}`;
    }

    onBulkHiatusStartInput(ev) { this.state.bulkHiatusStart = ev.target.value || ""; }
    onBulkHiatusEndInput(ev)   { this.state.bulkHiatusEnd   = ev.target.value || ""; }

    _addDaysIso(iso, days) {
        const d = new Date(iso + "T00:00:00");
        d.setDate(d.getDate() + days);
        return this._isoDate(d);
    }

    // Stage one hiatus op per selected row. The backend does the
    // heavy lifting on Save: it walks every schedule matching the
    // row's signature whose week overlaps [start, end] and strips
    // the hiatus-covered days from its days_allowed. No sibling
    // schedule is created - the schedule just stops running on
    // those days (falling into a new signature group).
    confirmBulkHiatus() {
        const start = (this.state.bulkHiatusStart || "").trim();
        const end   = (this.state.bulkHiatusEnd   || "").trim();
        if (!start || !end) {
            alert("Please pick both a Start Date and an End Date.");
            return;
        }
        if (end < start) {
            alert("End Date must be on or after Start Date.");
            return;
        }
        const ids = this.selectedRowIds;
        if (!ids.length) {
            alert("No rows selected.");
            return;
        }

        let affectedCount = 0;
        for (const rid of ids) {
            if (typeof rid === "string" && rid.startsWith("tmp:")) {
                continue;  // temp rows have no persisted schedules
            }
            const row = (this.state.payload.rows || []).find((r) => r.id === rid);
            if (!row) continue;

            console.log(row);
            
            const schedules = [];
            for (const cell of row.cells) {
                if (!cell.sched_id) continue;   // only real, persisted schedules

                // Which of this schedule's allowed weekdays land inside the
                // hiatus window. days_mask[i] -> i days after the week's
                // Monday (i = 0=Mon .. 6=Sun); cell.week is always a Monday.
                const hiatusDays = [];
                for (let i = 0; i < 7; i++) {
                    if (!row.days_mask[i]) continue;
                    const dayIso = this._addDaysIso(cell.week, i);
                    if (dayIso >= start && dayIso <= end) {
                        hiatusDays.push(i);
                    }
                }
                if (hiatusDays.length) {
                    schedules.push({
                        sched_id: cell.sched_id,
                        week: cell.week,
                        hiatus_days: hiatusDays,
                    });
                    affectedCount += 1;
                }
            }

            // Nothing in this row runs on a hiatus day - skip it entirely.
            if (!schedules.length) continue;

            const op = {
                row_id: rid,
                hiatus_start: start,
                hiatus_end: end,
                schedules: schedules,
            };
            this.state.edits.hiatus_ops.push(op);

            // Insert preview row(s) so the planner can see how the
            // grid will look AFTER Save.
            this._stageHiatusPreview(row, op);
        }

        this._markDirty();
        this.state.bulkAction = "";
        this.state.bulkHiatusStart = "";
        this.state.bulkHiatusEnd = "";
        this.clearSelection();
    }

    // Stage the visual preview for a single hiatus_op. For each
    // affected schedule we compute its post-hiatus days_bits (row's
    // current days_mask MINUS the hiatus days for THAT schedule),
    // group affected weeks by the resulting bits, and insert one
    // "PREVIEW" row per group directly below the original. The
    // original row's affected cells are dimmed to 'dashed' so the
    // planner can see the units moving into the preview row.
    // On Save, the backend actually mutates the schedules'
    // days_allowed; on Discard, loadGrid() replaces the whole payload
    // and the preview rows evaporate.
    _stageHiatusPreview(row, op) {
        if (!row || !op || !op.schedules || !op.schedules.length) return;

        // Group affected schedules by their post-hiatus 7-bit mask.
        const byBits = {};  // '1100000' -> { days_mask, entries: [...] }
        for (const s of op.schedules) {
            const removed = new Set(s.hiatus_days || []);
            const newMask = row.days_mask.map((v, i) => v && !removed.has(i));
            const bits = newMask.map((v) => (v ? "1" : "0")).join("");
            if (!byBits[bits]) {
                byBits[bits] = { days_mask: newMask, entries: [] };
            }
            byBits[bits].entries.push(s);
        }

        // Insertion index right after the original row.
        const rows = this.state.payload.rows;
        let insertAt = rows.indexOf(row);
        if (insertAt < 0) return;
        insertAt += 1;

        const weekList = this.state.payload.weeks || [];

        // For each new-bits group, build a preview row.
        for (const bits of Object.keys(byBits)) {
            const { days_mask, entries } = byBits[bits];
            const affectedWeekSet = new Set(entries.map((e) => e.week));
            // Map week -> the source cell so we can carry the units
            // across into the preview (visual continuity - user sees
            // where those units end up).
            const srcCellByWeek = {};
            for (const c of row.cells) srcCellByWeek[c.week] = c;

            const previewCells = weekList.map((wk) => {
                if (affectedWeekSet.has(wk)) {
                    const src = srcCellByWeek[wk] || {};
                    // All 7 days removed -> the preview row shows this
                    // week as cancelled (gray). Otherwise, keep the
                    // units and mark green.
                    const allRemoved = bits === "0000000";
                    return {
                        week: wk,
                        units: allRemoved ? 0 : (src.units || 0),
                        state: allRemoved ? "gray" : "green",
                        sched_id: false,   // no persistent id yet
                        cancelled_units: 0,
                        cancelled_sched_ids: [],
                        dirty: true,
                    };
                }
                return {
                    week: wk, units: 0, state: "dashed",
                    sched_id: false, cancelled_units: 0,
                    cancelled_sched_ids: [],
                };
            });

            this._tempCounter += 1;
            const previewKey = "hiatus-preview:" + this._tempCounter;
            const previewRow = {
                ...row,
                id: previewKey,
                _is_hiatus_preview: true,
                _is_ltc_preview: true,   // reuse existing preview styling
                _temp: this._tempCounter,
                days_mask: days_mask,
                cells: previewCells,
                total_spots: 0,
                total_revenue: 0,
                total_cancelled: 0,
            };
            rows.splice(insertAt, 0, previewRow);
            insertAt += 1;
        }

        // Dim the ORIGINAL row's cells for the affected weeks so the
        // planner sees the units 'leaving' the source row and
        // 'arriving' at the preview. Zero the units too - the preview
        // row is already displaying them, so leaving them here would
        // double-count visually.
        const affectedWeeks = new Set(op.schedules.map((s) => s.week));
        for (const cell of row.cells) {
            if (!affectedWeeks.has(cell.week)) continue;
            cell.units = 0;
            cell.cancelled_units = 0;
            cell.state = "dashed";
            cell.dirty = true;
        }
    }

    // ---- Update Rate bulk action ---------------------------------
    onBulkRateStartInput(ev) { this.state.bulkRateStart = ev.target.value || ""; }
    onBulkRateEndInput(ev)   { this.state.bulkRateEnd   = ev.target.value || ""; }
    onBulkRateValueInput(ev) { this.state.bulkRateValue = ev.target.value || ""; }

    // Stage one rate op per selected row. Payload:
    //   { row_id, rate_start, rate_end, new_rate,
    //     schedules: [{sched_id, week, units}] }
    // The backend handles this on Save: for each schedule in the op,
    // if all of its weeks fall inside [start, end] it just writes
    // the new rate; otherwise it keeps the original at the old rate
    // and creates a sibling schedule at the new rate for the
    // in-range weeks (which then land in a new signature group).
    confirmBulkRate() {
        const start = (this.state.bulkRateStart || "").trim();
        const end   = (this.state.bulkRateEnd   || "").trim();
        const raw   = (this.state.bulkRateValue || "").trim();
        if (!start || !end) {
            alert("Please pick both a Start Date and an End Date.");
            return;
        }
        if (end < start) {
            alert("End Date must be on or after Start Date.");
            return;
        }
        const newRate = parseFloat(raw);
        if (!Number.isFinite(newRate) || newRate < 0) {
            alert("Please enter a non-negative New Rate.");
            return;
        }
        const ids = this.selectedRowIds;
        if (!ids.length) {
            alert("No rows selected.");
            return;
        }
        for (const rid of ids) {
            if (typeof rid === "string" && rid.startsWith("tmp:")) {
                continue;  // temp rows have no persisted schedules
            }
            const row = (this.state.payload.rows || []).find((r) => r.id === rid);
            if (!row) continue;
            // No point re-writing the rate a schedule already has.
            if ((Number(row.rate) || 0) === newRate) continue;

            const schedules = [];
            for (const cell of row.cells) {
                if (!cell.sched_id) continue;
                // Only weeks whose Monday..Sunday span overlaps
                // [start, end] count. cell.week is always a Monday.
                const monIso = cell.week;
                const sunIso = this._addDaysIso(monIso, 6);
                if (sunIso < start || monIso > end) continue;
                schedules.push({
                    sched_id: cell.sched_id,
                    week: cell.week,
                    units: cell.units || 0,
                });
            }
            if (!schedules.length) continue;

            const op = {
                row_id: rid,
                rate_start: start,
                rate_end: end,
                new_rate: newRate,
                schedules: schedules,
            };
            this.state.edits.rate_ops.push(op);
            this._stageRatePreview(row, op);
        }
        this._markDirty();
        this.state.bulkAction = "";
        this.state.bulkRateStart = "";
        this.state.bulkRateEnd = "";
        this.state.bulkRateValue = "";
        this.clearSelection();
    }

    // Preview: insert one row grouped by the NEW rate below the
    // original, carrying the affected weeks' units. Dim the source
    // cells (and zero them) so the units don't appear twice.
    _stageRatePreview(row, op) {
        if (!row || !op || !op.schedules || !op.schedules.length) return;

        const rows = this.state.payload.rows;
        let insertAt = rows.indexOf(row);
        if (insertAt < 0) return;
        insertAt += 1;

        const weekList = this.state.payload.weeks || [];
        const affectedWeekSet = new Set(op.schedules.map((s) => s.week));
        const srcCellByWeek = {};
        for (const c of row.cells) srcCellByWeek[c.week] = c;

        const previewCells = weekList.map((wk) => {
            if (affectedWeekSet.has(wk)) {
                const src = srcCellByWeek[wk] || {};
                return {
                    week: wk,
                    units: src.units || 0,
                    state: (src.units || 0) > 0 ? "green" : "dashed",
                    sched_id: false,
                    cancelled_units: 0,
                    cancelled_sched_ids: [],
                    dirty: true,
                };
            }
            return {
                week: wk, units: 0, state: "dashed",
                sched_id: false, cancelled_units: 0,
                cancelled_sched_ids: [],
            };
        });

        this._tempCounter += 1;
        const previewKey = "rate-preview:" + this._tempCounter;
        // New rate -> new row_revenue calculation (units * new_rate).
        const totalSpots = previewCells.reduce(
            (a, c) => a + (Number(c.units) || 0), 0,
        );
        const previewRow = {
            ...row,
            id: previewKey,
            _is_rate_preview: true,
            _is_ltc_preview: true,   // reuse existing preview styling
            _temp: this._tempCounter,
            rate: op.new_rate,
            cells: previewCells,
            total_spots: totalSpots,
            total_revenue: totalSpots * op.new_rate,
            total_cancelled: 0,
        };
        rows.splice(insertAt, 0, previewRow);

        // Zero the source row's affected cells so units don't
        // appear twice on screen.
        const affectedWeeks = affectedWeekSet;
        for (const cell of row.cells) {
            if (!affectedWeeks.has(cell.week)) continue;
            cell.units = 0;
            cell.cancelled_units = 0;
            cell.state = "dashed";
            cell.dirty = true;
        }
    }

    cancelBulkAction() {
        this.state.bulkAction = "";
    }

    onBulkMaxDayInput(ev) {
        this.state.bulkMaxDay = ev.target.value || "";
    }

    // Apply the typed Max/Day value to every selected row. Each
    // affected row gets row.max_per_day updated locally and a queued
    // row_update with max_per_day. save_units_grid then updates every
    // schedule matching the row's signature to the new max_per_day
    // (which itself IS part of the signature, so those schedules
    // roll into a new sig group after the write).
    confirmBulkMaxDay() {
        const raw = this.state.bulkMaxDay;
        const n = parseInt(raw, 10);
        if (!Number.isFinite(n) || n < 0) {
            alert("Please enter a non-negative Max/Day value.");
            return;
        }
        const ids = this.selectedRowIds;
        if (!ids.length) {
            alert("No rows selected.");
            return;
        }
        const targets = (this.state.payload.rows || []).filter(
            (r) => !r._is_ltc_preview && this.state.selected[r.id],
        );
        for (const row of targets) {
            row.max_per_day = n;
            const upd = this._findOrPushRowUpdate(row);
            upd.max_per_day = n;
        }
        this._markDirty();
        this.state.bulkAction = "";
        this.state.bulkMaxDay = "";
        this.clearSelection();
    }

    applyBulkLtc() {
        const dateIso = this.state.bulkLtcDate;
        if (!dateIso) {
            alert("Please pick an LTC date before clicking Apply.");
            return;
        }
        const ids = this.selectedRowIds;
        if (!ids.length) {
            alert("No rows selected.");
            return;
        }
        // Iterate a snapshot of rows that match the selected ids. We
        // snapshot first because _stageLtc mutates state.payload.rows
        // (inserts preview rows) which would shift indexes.
        const targets = (this.state.payload.rows || []).filter(
            (r) => !r._is_ltc_preview && this.state.selected[r.id],
        );
        for (const row of targets) {
            this._stageLtc(row, dateIso);
        }
        // Close the modal, clear bulk state, drop the selection.
        this.state.bulkAction = "";
        this.state.bulkLtcDate = "";
        this.clearSelection();
    }

    // Stage an LTC operation locally:
    //  1) Cancel post-LTC-week active cells in the original row
    //     (move units -> cancelled_units, units -> 0).
    //  2) If the LTC week's days_allowed truncates (Mon..weekday(LTC)
    //     differs from row.days_mask), build a PREVIEW row showing
    //     the split: same daypart/rate/times, new days_mask, and
    //     the LTC-week unit count moved over. The original row's
    //     LTC-week cell is cleared.
    //  3) Queue an ltc_op on state.edits so save_units_grid runs the
    //     canonical _do_apply_ltc on the backend.
    // Discard reverts everything via resetEdits + loadGrid.
    _stageLtc(row, dateIso) {
        // Skip if this is already a preview row (shouldn't happen via
        // UI but guard anyway).
        if (row._is_ltc_preview) return;    

        const ltcDate = new Date(dateIso + "T00:00:00");
        const wMon0 = (ltcDate.getDay() + 6) % 7; // Mon=0..Sun=6
        const ltcMon = new Date(ltcDate);
        ltcMon.setDate(ltcMon.getDate() - wMon0);
        const y = ltcMon.getFullYear();
        const m = String(ltcMon.getMonth() + 1).padStart(2, "0");
        const dd = String(ltcMon.getDate()).padStart(2, "0");
        const ltcMonIso = `${y}-${m}-${dd}`;

        const rowId = row._is_new ? "tmp:" + row._temp : row.id;

        // (1) Cancel post-LTC-week cells with active data.
        for (const cell of row.cells) {
            if (cell.week <= ltcMonIso) continue;
            const activeUnits = Number(cell.units) || 0;
            const hasActive = !!cell.sched_id || activeUnits > 0;
            if (!hasActive) continue;
            cell.cancelled_units = (Number(cell.cancelled_units) || 0)
                                   + activeUnits;
            cell.units = 0;
            cell.state = "dashed";
            cell.dirty = true;
            const idx = this.state.edits.cell_updates.findIndex(
                (e) => e.row_id === rowId && e.week === cell.week
            );
            if (idx !== -1) this.state.edits.cell_updates.splice(idx, 1);
            this.state.edits.cell_updates.push({
                row_id: rowId, week: cell.week, cancelled: true,
            });
        }

        // (2) Build the truncated-days preview row if needed.
        const ltcWeekday = wMon0;  // weekday-of-LTC, Mon=0..Sun=6
        const newDaysMask = row.days_mask.map(
            (on, i) => Boolean(on) && i <= ltcWeekday,
        );
        const sameDays = newDaysMask.every(
            (v, i) => Boolean(v) === Boolean(row.days_mask[i]),
        );
        if (!sameDays) {
            const ltcCell = row.cells.find((c) => c.week === ltcMonIso);
            const movedUnits = ltcCell ? (Number(ltcCell.units) || 0) : 0;

            // Build cells for the preview row - dashed except the LTC week.
            const previewCells = (this.state.payload.weeks || []).map(
                (w) => ({
                    week: w,
                    units: w === ltcMonIso ? movedUnits : 0,
                    state: w === ltcMonIso && movedUnits > 0
                           ? "green" : "dashed",
                    sched_id: false,
                    cancelled_units: 0,
                    cancelled_sched_ids: [],
                }),
            );

            this._ltcPreviewCounter = (this._ltcPreviewCounter || 0) + 1;
            const previewRow = {
                id: `ltc-preview:${this._ltcPreviewCounter}`,
                _is_ltc_preview: true,
                daypart: row.daypart,
                daypart_label: row.daypart_label,
                time_range: row.time_range,
                start_time: row.start_time,
                end_time: row.end_time,
                days_mask: newDaysMask,
                rate: row.rate,
                run_start: row.run_start,
                run_end: row.run_end,
                cells: previewCells,
                total_spots: movedUnits,
                total_revenue: movedUnits * (Number(row.rate) || 0),
                total_cancelled: 0,
            };

            // Insert the preview right after the original row.
            const idx = this.state.payload.rows.findIndex(
                (r) => r.id === row.id,
            );
            if (idx >= 0) {
                this.state.payload.rows.splice(idx + 1, 0, previewRow);
            } else {
                this.state.payload.rows.push(previewRow);
            }

            // Clear the LTC-week cell on the original row (the units
            // visually "moved" into the new split row).
            if (ltcCell) {
                ltcCell.units = 0;
                ltcCell.state = "dashed";
                ltcCell.dirty = true;
            }
        }

        // (3) Queue the LTC op for the backend.
        this.state.edits.ltc_ops = this.state.edits.ltc_ops || [];
        this.state.edits.ltc_ops.push({
            row_id: rowId, ltc_date: dateIso,
        });

        this._markDirty();
        this._recomputeTotals();
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
        const sym = (cur && cur.symbol) || "$";
        const n = Number(amount || 0).toLocaleString(undefined, {
            minimumFractionDigits: 0, maximumFractionDigits: 0,
        });
        return cur && cur.position === "after" ? n + sym : sym + n;
    }

    fmtWeekShort(iso) {
        if (!iso) return "";
        const d = new Date(iso + "T00:00:00");
        return (d.getMonth() + 1) + "/" + d.getDate();
    }

    // Returns a URL that opens the schedule record's form view in a
    // new browser tab. Used by the eye icon under each Units cell.
    //
    // We use the ACTION URL (/odoo/action-<xmlid>/<id>) rather than
    // the raw record URL (/odoo/<model>/<id>). The raw record URL
    // hides the top Odoo app menu bar because it has no action
    // context; the action URL puts the record inside the standard
    // Schedules list action so the top nav (Marathon Ventures /
    // Master Data / Sales Operations / ...) stays visible - matching
    // what the planner sees when opening a schedule through the
    // Sales Operations -> Schedules menu.
    scheduleOpenUrl(cell) {
        if (!cell || !cell.sched_id) return "#";
        return `/odoo/action-marathon_ventures.action_mv_schedules/${cell.sched_id}`;
    }
}


registry.category("fields").add("mv_units_grid", {
    component: MvUnitsGrid,
    supportedTypes: ["integer"],
});
