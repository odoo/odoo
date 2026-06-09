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
    onCapPctInput(row, cell, ev) {
        if (cell.state === 'hatched' || cell.state === 'dashed') return;
        let n = parseInt(ev.target.value, 10);
        if (!Number.isFinite(n)) n = 100;
        n = Math.max(0, Math.min(100, n));
        cell.cap_pct = n;
        cell.units_effective = Math.round((cell.units_booked || 0) * n / 100 * 100) / 100;
        if (n >= 100) cell.state = 'green';
        else if (n === 0) cell.state = 'gray';
        else cell.state = 'amber';
        cell.dirty = true;
        // Use sched_id as the lookup key on the server. We also send
        // row_id + week as a fallback in case sched_id is missing.
        const list = this.state.edits.cell_updates;
        const found = list.find((e) => e.sched_id === cell.sched_id);
        if (found) {
            found.cap_pct = n;
        } else {
            list.push({
                sched_id: cell.sched_id,
                row_id: row.id,
                week: cell.week,
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
        return Object.keys(this.state.selected)
            .filter((k) => this.state.selected[k])
            .map((k) => parseInt(k, 10) || k);
    }

    clearSelection() {
        this.state.selected = {};
    }

    async setBulkCapPct() {
        const ids = this.selectedRowIds;
        if (!ids.length) return;
        const raw = window.prompt("Set cap % for the selected rows (0-100):", "100");
        if (raw === null) return;
        let pct = parseInt(raw, 10);
        if (!Number.isFinite(pct)) return;
        pct = Math.max(0, Math.min(100, pct));
        for (const rid of ids) {
            this.state.edits.row_cap_pct.push({ row_id: rid, cap_pct: pct });
            // Update local row cells too for instant feedback
            const row = this.state.payload.rows.find((r) => r.id === rid);
            if (row) {
                for (const c of row.cells) {
                    if (c.state === 'hatched' || c.state === 'dashed') continue;
                    c.cap_pct = pct;
                    c.units_effective = Math.round((c.units_booked || 0) * pct / 100 * 100) / 100;
                    if (pct >= 100) c.state = 'green';
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

    onDiscard() { this.loadGrid(); }

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
