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
        this.state.loaded = true;
        this.resetEdits();
    }

    resetEdits() {
        this.state.edits = { row_updates: [], row_creates: [], row_deletes: [], cell_updates: [] };
        this.state.dirty = false;
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
        this.state.edits.row_creates.push({
            temp_id: tempKey,
            daypart: newRow.daypart,
            time_range: newRow.time_range,
            days_mask: newRow.days_mask.slice(),
            rate: newRow.rate,
            run_start: newRow.run_start,
            run_end: newRow.run_end,
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
        let gs = 0, gr = 0;
        for (const row of this.state.payload.rows) {
            let s = 0;
            for (const c of row.cells) s += Number(c.units) || 0;
            row.total_spots = s;
            row.total_revenue = s * (Number(row.rate) || 0);
            gs += s;
            gr += row.total_revenue;
        }
        this.state.payload.grand_total_spots = gs;
        this.state.payload.grand_total_revenue = gr;
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
        this.loadGrid();  // reloads from server, dumping local edits
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
