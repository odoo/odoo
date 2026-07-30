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
        this.versionRequestId = 0;
        this.resultRequestId = 0;

        this.state = useState({
            loaded: false,
            querying: false,
            attaching: false,
            exporting: false,
            hasFiltered: false,
            programs: [],
            versions: [],
            pageSize: 200,
            timeBufferMinutes: 120,
            filters: {
                programId: false,
                weekStart: "",
                version: false,
            },
            rows: [],
            total: 0,
            offset: 0,
            page: 0,
            pages: 0,
            selections: {},
            manualValues: {},
        });

        onWillStart(async () => {
            const options = await this.orm.call(
                "mv.prelog_data",
                "fuzzy_match_get_options",
                [],
            );
            this._setOptions(options);
            this.state.loaded = true;
        });
    }

    _setOptions(options) {
        options = options || {};
        if (options.programs) {
            this.state.programs = options.programs;
        }
        this.state.versions = options.versions || [];
        this.state.pageSize = options.page_size || 200;
        this.state.timeBufferMinutes = options.time_buffer_minutes || 120;
    }

    async _refreshVersions() {
        const { programId, weekStart } = this.state.filters;
        const requestId = ++this.versionRequestId;
        this.state.versions = [];
        this.state.filters.version = false;
        if (!programId || !weekStart) {
            return;
        }
        const options = await this.orm.call(
            "mv.prelog_data",
            "fuzzy_match_get_options",
            [Number(programId), weekStart],
        );
        if (requestId !== this.versionRequestId) {
            return;
        }
        this._setOptions(options);
    }

    async onProgramChange(ev) {
        this._invalidateResults();
        this.state.filters.programId = Number(ev.target.value) || false;
        await this._refreshVersions();
    }

    async onWeekChange(ev) {
        this._invalidateResults();
        this.state.filters.weekStart = ev.target.value;
        await this._refreshVersions();
    }

    onVersionChange(ev) {
        this._invalidateResults();
        this.state.filters.version = Number(ev.target.value) || false;
    }

    _invalidateResults() {
        this.versionRequestId += 1;
        this.resultRequestId += 1;
        this.state.querying = false;
        this.state.hasFiltered = false;
        this.state.rows = [];
        this.state.total = 0;
        this.state.offset = 0;
        this.state.page = 0;
        this.state.pages = 0;
        this.state.selections = {};
        this.state.manualValues = {};
    }

    _filtersAreComplete() {
        const filters = this.state.filters;
        if (!filters.programId || !filters.weekStart || !filters.version) {
            this.notification.add(
                "Select a Program, Monday week, and version first.",
                { type: "warning" },
            );
            return false;
        }
        const date = new Date(`${filters.weekStart}T12:00:00`);
        if (Number.isNaN(date.getTime()) || date.getDay() !== 1) {
            this.notification.add(
                "Week must be the Monday that starts the broadcast week.",
                { type: "warning" },
            );
            return false;
        }
        return true;
    }

    async onFilter() {
        if (!this._filtersAreComplete()) {
            return;
        }
        this.state.offset = 0;
        this.state.selections = {};
        this.state.manualValues = {};
        await this._loadResults();
    }

    async _loadResults() {
        const requestId = ++this.resultRequestId;
        const programId = Number(this.state.filters.programId);
        const weekStart = this.state.filters.weekStart;
        const version = Number(this.state.filters.version);
        this.state.querying = true;
        try {
            const result = await this.orm.call(
                "mv.prelog_data",
                "fuzzy_match_search",
                [
                    programId,
                    weekStart,
                    version,
                    this.state.offset,
                    this.state.pageSize,
                ],
            );
            if (requestId !== this.resultRequestId) {
                return;
            }
            this.state.rows = result.rows || [];
            this.state.total = result.total || 0;
            this.state.offset = result.offset || 0;
            this.state.page = result.page || 0;
            this.state.pages = result.pages || 0;
            this.state.hasFiltered = true;
        } finally {
            if (requestId === this.resultRequestId) {
                this.state.querying = false;
            }
        }
    }

    get selectedCount() {
        return Object.keys(this.state.selections).length;
    }

    get visibleRangeStart() {
        return this.state.total ? this.state.offset + 1 : 0;
    }

    get visibleRangeEnd() {
        return Math.min(
            this.state.offset + this.state.pageSize,
            this.state.total,
        );
    }

    isSuggestedSelected(row) {
        const selection = this.state.selections[row.id];
        return Boolean(selection && selection.source === "suggested");
    }

    isManualSelected(row) {
        const selection = this.state.selections[row.id];
        return Boolean(selection && selection.source === "manual");
    }

    onSuggestedToggle(row, ev) {
        if (ev.target.checked) {
            this.state.selections[row.id] = {
                prelog_id: row.id,
                schedule_id: row.suggested.id,
                schedule_ref: "",
                source: "suggested",
                confirmed_override: false,
                risky: Boolean(row.reason),
            };
        } else {
            delete this.state.selections[row.id];
        }
    }

    onManualInput(row, ev) {
        const value = ev.target.value;
        this.state.manualValues[row.id] = value;
        const selection = this.state.selections[row.id];
        if (!value.trim() && selection && selection.source === "manual") {
            delete this.state.selections[row.id];
        } else if (selection && selection.source === "manual") {
            selection.schedule_ref = value.trim();
        }
    }

    onManualToggle(row, ev) {
        const value = (this.state.manualValues[row.id] || "").trim();
        if (ev.target.checked && value) {
            this.state.selections[row.id] = {
                prelog_id: row.id,
                schedule_id: false,
                schedule_ref: value,
                source: "manual",
                confirmed_override: false,
                risky: true,
            };
        } else {
            delete this.state.selections[row.id];
        }
    }

    async onAttach() {
        const selected = Object.values(this.state.selections);
        if (!selected.length) {
            this.notification.add(
                "Select at least one suggested or manual schedule.",
                { type: "info" },
            );
            return;
        }

        const risky = selected.filter((item) => item.risky);
        if (risky.length) {
            const confirmed = window.confirm(
                `${risky.length} selected row(s) contain a mismatch or manual override. ` +
                "Attach the schedules anyway?",
            );
            if (!confirmed) {
                return;
            }
            for (const item of selected) {
                if (item.risky) {
                    item.confirmed_override = true;
                }
            }
        }

        const appliedFilters = {
            programId: Number(this.state.filters.programId),
            weekStart: this.state.filters.weekStart,
            version: Number(this.state.filters.version),
        };
        this.state.attaching = true;
        try {
            const payload = selected.map((item) => ({
                prelog_id: item.prelog_id,
                schedule_id: item.schedule_id || false,
                schedule_ref: item.schedule_ref || "",
                source: item.source,
                confirmed_override: Boolean(item.confirmed_override),
            }));
            const result = await this.orm.call(
                "mv.prelog_data",
                "fuzzy_match_apply",
                [
                    payload,
                    appliedFilters.programId,
                    appliedFilters.weekStart,
                    appliedFilters.version,
                ],
            );
            this.notification.add(result.message, { type: "success" });
            this.state.selections = {};
            this.state.manualValues = {};
            if (this._filtersMatch(appliedFilters)) {
                const versionsRefreshed = await this._refreshVersionsKeepingSelection(
                    appliedFilters.version,
                );
                if (versionsRefreshed && this._filtersMatch(appliedFilters)) {
                    await this._loadResults();
                }
            } else {
                this._invalidateResults();
            }
        } finally {
            this.state.attaching = false;
        }
    }

    _filtersMatch(filters) {
        return (
            Number(this.state.filters.programId) === filters.programId &&
            this.state.filters.weekStart === filters.weekStart &&
            Number(this.state.filters.version) === filters.version
        );
    }

    async _refreshVersionsKeepingSelection(currentVersion) {
        const requestId = ++this.versionRequestId;
        const programId = Number(this.state.filters.programId);
        const weekStart = this.state.filters.weekStart;
        const options = await this.orm.call(
            "mv.prelog_data",
            "fuzzy_match_get_options",
            [
                programId,
                weekStart,
            ],
        );
        if (
            requestId !== this.versionRequestId ||
            programId !== Number(this.state.filters.programId) ||
            weekStart !== this.state.filters.weekStart
        ) {
            return false;
        }
        this._setOptions(options);
        if (!this.state.versions.includes(currentVersion)) {
            this.state.versions.push(currentVersion);
            this.state.versions.sort((a, b) => a - b);
        }
        this.state.filters.version = currentVersion;
        return true;
    }

    async onExport() {
        if (!this._filtersAreComplete()) {
            return;
        }
        this.state.exporting = true;
        try {
            const result = await this.orm.call(
                "mv.prelog_data",
                "fuzzy_match_export_csv",
                [
                    Number(this.state.filters.programId),
                    this.state.filters.weekStart,
                    Number(this.state.filters.version),
                ],
            );
            const blob = new Blob(["\ufeff", result.content || ""], {
                type: "text/csv;charset=utf-8",
            });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = result.filename || "PrelogFuzzyMatching.csv";
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            this.notification.add(
                `${result.count || 0} exception row(s) exported.`,
                { type: "success" },
            );
        } finally {
            this.state.exporting = false;
        }
    }

    async previousPage() {
        if (this.state.offset <= 0) {
            return;
        }
        this.state.offset = Math.max(
            this.state.offset - this.state.pageSize,
            0,
        );
        await this._loadResults();
    }

    async nextPage() {
        if (this.state.offset + this.state.pageSize >= this.state.total) {
            return;
        }
        this.state.offset += this.state.pageSize;
        await this._loadResults();
    }

    cellClass(row, mismatch = false) {
        if (mismatch) {
            return "mv-fuzzy__cell mv-fuzzy__cell--mismatch";
        }
        if (row.suggested) {
            return "mv-fuzzy__cell mv-fuzzy__cell--suggested";
        }
        return "mv-fuzzy__cell mv-fuzzy__cell--missing";
    }

    formatRate(value) {
        const number = Number(value || 0);
        return Number.isFinite(number)
            ? number.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            })
            : "";
    }

    async openPrelog(row) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: row.name,
            res_model: "mv.prelog_data",
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openSchedule(schedule) {
        if (!schedule) {
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: schedule.name,
            res_model: "mv.schedules",
            res_id: schedule.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add(
    "mv_prelog_fuzzy_matching",
    MvPrelogFuzzyMatching,
);
