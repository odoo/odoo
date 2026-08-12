/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class MvPrelogFuzzyMatching extends Component {
    static template = "marathon_ventures.MvPrelogFuzzyMatching";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.requestId = 0;
        this.state = useState({
            loaded: false,
            querying: false,
            mutating: false,
            exporting: false,
            hasFiltered: false,
            programs: [],
            versions: [],
            latestUpload: false,
            pageSize: 200,
            timeBufferMinutes: 120,
            filters: { programId: false, weekStart: "", version: false, importJobId: false },
            activeTab: "all",
            counts: { all: 0, matched: 0, suggestions: 0, no_suggestion: 0, removed: 0 },
            searchTerm: "",
            airDate: "",
            issueFilter: "",
            sortBy: "air_date",
            rows: [],
            total: 0,
            offset: 0,
            page: 0,
            pages: 0,
            selectedRows: {},
            drawerRow: false,
            manualSchedule: "",
        });

        onWillStart(async () => {
            const options = await this.orm.call("mv.prelog_data", "fuzzy_match_get_options", []);
            this._setOptions(options, true);
            const latest = this.state.latestUpload;
            if (latest) {
                this.state.filters.programId = latest.program_id;
                this.state.filters.weekStart = latest.week_start;
                this.state.filters.version = latest.version;
                this.state.filters.importJobId = latest.id;
                await this._refreshVersions(latest.version);
                await this._loadResults();
            }
            this.state.loaded = true;
        });
    }

    _setOptions(options, includeLatest = false) {
        options = options || {};
        this.state.programs = options.programs || this.state.programs;
        this.state.versions = options.versions || [];
        this.state.pageSize = options.page_size || 200;
        this.state.timeBufferMinutes = options.time_buffer_minutes || 120;
        if (includeLatest) {
            this.state.latestUpload = options.latest_upload || false;
        }
    }

    async _refreshVersions(keepVersion = false) {
        const { programId, weekStart } = this.state.filters;
        this.state.versions = [];
        if (!programId || !weekStart) {
            this.state.filters.version = false;
            return;
        }
        const options = await this.orm.call(
            "mv.prelog_data", "fuzzy_match_get_options", [Number(programId), weekStart]
        );
        this._setOptions(options);
        if (keepVersion && !this.state.versions.includes(Number(keepVersion))) {
            this.state.versions.push(Number(keepVersion));
            this.state.versions.sort((a, b) => a - b);
        }
        this.state.filters.version = keepVersion ? Number(keepVersion) : false;
    }

    _clearResults() {
        this.requestId += 1;
        this.state.hasFiltered = false;
        this.state.rows = [];
        this.state.total = 0;
        this.state.offset = 0;
        this.state.selectedRows = {};
        this.state.drawerRow = false;
    }

    async onProgramChange(ev) {
        this._clearResults();
        this.state.filters.programId = Number(ev.target.value) || false;
        this.state.filters.importJobId = false;
        await this._refreshVersions();
    }

    async onWeekChange(ev) {
        this._clearResults();
        this.state.filters.weekStart = ev.target.value;
        this.state.filters.importJobId = false;
        await this._refreshVersions();
    }

    onVersionChange(ev) {
        this._clearResults();
        this.state.filters.version = Number(ev.target.value) || false;
        this.state.filters.importJobId = false;
    }

    _filtersAreComplete() {
        const filters = this.state.filters;
        if (!filters.programId || !filters.weekStart || !filters.version) {
            this.notification.add("Select a Program, Monday week, and version first.", { type: "warning" });
            return false;
        }
        const date = new Date(`${filters.weekStart}T12:00:00`);
        if (Number.isNaN(date.getTime()) || date.getDay() !== 1) {
            this.notification.add("Week must be the Monday that starts the broadcast week.", { type: "warning" });
            return false;
        }
        return true;
    }

    async onFilter() {
        if (!this._filtersAreComplete()) return;
        this.state.offset = 0;
        this.state.selectedRows = {};
        await this._loadResults();
    }

    async onSearchKeydown(ev) {
        if (ev.key === "Enter") await this.onFilter();
    }

    async setTab(tab) {
        if (this.state.querying || tab === this.state.activeTab) return;
        this.state.activeTab = tab;
        this.state.offset = 0;
        this.state.selectedRows = {};
        this.state.drawerRow = false;
        await this._loadResults();
    }

    _queryArgs() {
        const f = this.state.filters;
        return [
            Number(f.programId), f.weekStart, Number(f.version), this.state.offset,
            this.state.pageSize, this.state.activeTab, this.state.searchTerm,
            this.state.airDate || false, this.state.issueFilter, this.state.sortBy,
            f.importJobId || false,
        ];
    }

    async _loadResults() {
        const requestId = ++this.requestId;
        this.state.querying = true;
        try {
            const result = await this.orm.call("mv.prelog_data", "fuzzy_match_search", this._queryArgs());
            if (requestId !== this.requestId) return;
            this.state.rows = result.rows || [];
            this.state.total = result.total || 0;
            this.state.offset = result.offset || 0;
            this.state.page = result.page || 0;
            this.state.pages = result.pages || 0;
            this.state.counts = result.counts || this.state.counts;
            this.state.hasFiltered = true;
        } finally {
            if (requestId === this.requestId) this.state.querying = false;
        }
    }

    get selectedCount() { return Object.keys(this.state.selectedRows).length; }
    get visibleRangeStart() { return this.state.total ? this.state.offset + 1 : 0; }
    get visibleRangeEnd() { return Math.min(this.state.offset + this.state.pageSize, this.state.total); }
    get allPageSelected() {
        return Boolean(this.state.rows.length) && this.state.rows.every((row) => this.state.selectedRows[row.id]);
    }

    isSelected(row) { return Boolean(this.state.selectedRows[row.id]); }
    toggleRow(row, ev) {
        if (ev.target.checked) this.state.selectedRows[row.id] = true;
        else delete this.state.selectedRows[row.id];
    }
    toggleAll(ev) {
        for (const row of this.state.rows) {
            if (ev.target.checked) this.state.selectedRows[row.id] = true;
            else delete this.state.selectedRows[row.id];
        }
    }
    selectedRows() { return this.state.rows.filter((row) => this.state.selectedRows[row.id]); }

    async attachSuggested() {
        const rows = this.selectedRows().filter(
            (row) => row.status === "suggestion" && row.suggested && row.suggestion_attachable
        );
        if (!rows.length) {
            this.notification.add("Select one or more rows with attachable suggestions.", { type: "info" });
            return;
        }
        const risky = rows.filter((row) => row.match_quality !== "exact");
        if (risky.length && !window.confirm(
            `${risky.length} selected suggestion(s) are fuzzy or contain a mismatch. Attach anyway?`
        )) return;
        const payload = rows.map((row) => ({
            prelog_id: row.id, schedule_id: row.suggested.id, schedule_ref: "",
            source: "suggested", confirmed_override: row.match_quality !== "exact",
        }));
        await this._applySchedules(payload);
    }

    async attachOneSuggestion(row) {
        this.state.selectedRows = { [row.id]: true };
        await this.attachSuggested();
    }

    async _applySchedules(payload) {
        const f = this.state.filters;
        this.state.mutating = true;
        try {
            const result = await this.orm.call("mv.prelog_data", "fuzzy_match_apply", [
                payload, Number(f.programId), f.weekStart, Number(f.version),
            ]);
            this.notification.add(result.message, { type: "success" });
            this.state.selectedRows = {};
            this.state.drawerRow = false;
            await this._loadResults();
        } finally { this.state.mutating = false; }
    }

    async setRemoved(removed, row = false) {
        const ids = row ? [row.id] : this.selectedRows().map((item) => item.id);
        if (!ids.length) {
            this.notification.add("Select at least one Prelog row.", { type: "info" });
            return;
        }
        const verb = removed ? "remove" : "unremove";
        const warning = removed
            ? `Remove ${ids.length} row(s)? Any attached Schedule ID will be cleared.`
            : `Unremove ${ids.length} row(s)? Schedule suggestions will be recalculated.`;
        if (!window.confirm(warning)) return;
        const f = this.state.filters;
        this.state.mutating = true;
        try {
            const result = await this.orm.call("mv.prelog_data", "fuzzy_match_set_removed", [
                ids, removed, Number(f.programId), f.weekStart, Number(f.version), f.importJobId || false,
            ]);
            this.notification.add(result.message || `${ids.length} row(s) ${verb}d.`, { type: "success" });
            this.state.selectedRows = {};
            this.state.drawerRow = false;
            await this._loadResults();
        } finally { this.state.mutating = false; }
    }

    async detachSchedule(row) {
        if (!window.confirm(`Detach ${row.attached?.name || "the schedule"} from this Prelog row?`)) return;
        const f = this.state.filters;
        this.state.mutating = true;
        try {
            const result = await this.orm.call("mv.prelog_data", "fuzzy_match_detach", [[
                row.id,
            ], Number(f.programId), f.weekStart, Number(f.version), f.importJobId || false]);
            this.notification.add(result.message, { type: "success" });
            this.state.drawerRow = false;
            await this._loadResults();
        } finally { this.state.mutating = false; }
    }

    async attachManual(row) {
        const reference = this.state.manualSchedule.trim();
        if (!reference) {
            this.notification.add("Enter a schedule name or Odoo ID.", { type: "warning" });
            return;
        }
        const replacing = row.status === "matched";
        if (!window.confirm(`${replacing ? "Replace the current" : "Attach this"} schedule using a manual override?`)) return;
        await this._applySchedules([{
            prelog_id: row.id, schedule_id: false, schedule_ref: reference,
            source: "manual", confirmed_override: true, replace_existing: replacing,
        }]);
    }

    openDrawer(row) {
        this.state.drawerRow = row;
        this.state.manualSchedule = "";
    }
    closeDrawer() { this.state.drawerRow = false; this.state.manualSchedule = ""; }

    async onExport() {
        if (!this._filtersAreComplete()) return;
        const f = this.state.filters;
        this.state.exporting = true;
        try {
            const result = await this.orm.call("mv.prelog_data", "fuzzy_workbench_export_csv", [
                Number(f.programId), f.weekStart, Number(f.version), this.state.activeTab,
                this.state.searchTerm, this.state.airDate || false, this.state.issueFilter,
                this.state.sortBy, f.importJobId || false,
            ]);
            const blob = new Blob(["\ufeff", result.content || ""], { type: "text/csv;charset=utf-8" });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url; link.download = result.filename || "PrelogWorkbench.csv";
            document.body.appendChild(link); link.click(); link.remove(); window.URL.revokeObjectURL(url);
            this.notification.add(`${result.count || 0} row(s) exported.`, { type: "success" });
        } finally { this.state.exporting = false; }
    }

    async previousPage() {
        if (this.state.offset <= 0) return;
        this.state.offset = Math.max(this.state.offset - this.state.pageSize, 0);
        await this._loadResults();
    }
    async nextPage() {
        if (this.state.offset + this.state.pageSize >= this.state.total) return;
        this.state.offset += this.state.pageSize;
        await this._loadResults();
    }

    formatRate(value) {
        const number = Number(value || 0);
        return Number.isFinite(number) ? number.toLocaleString(undefined, {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        }) : "";
    }
    statusBadge(row) { return `mv-fuzzy__status mv-fuzzy__status--${row.status}`; }

    async openPrelog(row) {
        await this.action.doAction({
            type: "ir.actions.act_window", name: row.name, res_model: "mv.prelog_data",
            res_id: row.id, views: [[false, "form"]], target: "current",
        });
    }
    async openSchedule(schedule) {
        if (!schedule) return;
        await this.action.doAction({
            type: "ir.actions.act_window", name: schedule.name, res_model: "mv.schedules",
            res_id: schedule.id, views: [[false, "form"]], target: "current",
        });
    }
}

registry.category("actions").add("mv_prelog_fuzzy_matching", MvPrelogFuzzyMatching);
