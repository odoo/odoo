/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { translate, getActiveLang } from "../i18n";

export class AgingPiutangView extends Component {
    static template = "sif_keuangan.AgingPiutangView";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        const todayStr = `${yyyy}-${mm}-${dd}`;

        const actionParams = this.props.action?.params || {};
        const initialAsOfDate = actionParams.as_of_date || todayStr;
        const initialUnitName = actionParams.unit_name || "";
        const initialPartnerType = actionParams.partner_type || "all";
        const initialBucket = actionParams.bucket || "all";
        const initialSearch = actionParams.search || "";
        const initialView = actionParams.view_mode || "tree"; // 'tree', 'matrix', 'list', 'kanban'

        this.state = useState({
            filters: {
                as_of_date: initialAsOfDate,
                unit_name: initialUnitName,
                partner_type: initialPartnerType,
                bucket: initialBucket,
                search: initialSearch,
                comparison_type: "none",
                comparison_date: "",
                target_move: "posted",
                lang: getActiveLang(),
            },
            searchQuery: initialSearch,
            activeView: initialView, // 'tree', 'matrix', 'list', 'kanban'
            showBreakdown: true, // Breakdown > 90 hari (5 bucket vs 8 bucket)
            data: null,
            loading: true,
            datePreset: "today",
            customAsOfDate: initialAsOfDate,
            unfoldedPartners: {},
            sortField: "total",
            sortAsc: false,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    t(key, params = {}) {
        return translate(key, params);
    }

    formatRp(val) {
        if (val === undefined || val === null) return "Rp 0,00";
        const num = Number(val);
        if (isNaN(num)) return "Rp 0,00";
        const formatted = Math.abs(num).toLocaleString("id-ID", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return (num < 0 ? "-Rp " : "Rp ") + formatted;
    }

    async loadData() {
        this.state.loading = true;
        try {
            const filters = {
                ...this.state.filters,
                search: this.state.searchQuery || "",
                lang: getActiveLang(),
            };
            const result = await this.orm.call(
                "sif.aging.piutang",
                "get_aging_piutang_data",
                [filters]
            );
            this.state.data = result;
        } catch (error) {
            console.error("Error loading Aging Piutang data:", error);
            this.notification.add(
                error.message || "Gagal memuat data Aging Piutang.",
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        this.state.filters.search = ev.target.value;
        this.loadData();
    }

    onResetSearch() {
        this.state.searchQuery = "";
        this.state.filters.search = "";
        this.loadData();
    }

    setView(viewMode) {
        this.state.activeView = viewMode;
    }

    toggleBreakdown() {
        this.state.showBreakdown = !this.state.showBreakdown;
    }

    togglePartner(partnerKey) {
        if (this.state.unfoldedPartners[partnerKey]) {
            delete this.state.unfoldedPartners[partnerKey];
        } else {
            this.state.unfoldedPartners[partnerKey] = true;
        }
    }

    isPartnerUnfolded(partnerKey) {
        return Boolean(this.state.unfoldedPartners[partnerKey]);
    }

    unfoldAll() {
        if (!this.state.data || !this.state.data.partners) return;
        const unfolded = {};
        for (const p of this.state.data.partners) {
            unfolded[p.partner_key] = true;
        }
        this.state.unfoldedPartners = unfolded;
    }

    foldAll() {
        this.state.unfoldedPartners = {};
    }

    onSort(field) {
        if (this.state.sortField === field) {
            this.state.sortAsc = !this.state.sortAsc;
        } else {
            this.state.sortField = field;
            this.state.sortAsc = false;
        }
    }

    get sortedPartners() {
        if (!this.state.data || !this.state.data.partners) return [];
        const list = [...this.state.data.partners];
        const field = this.state.sortField;
        const asc = this.state.sortAsc;

        list.sort((a, b) => {
            let va = a[field];
            let vb = b[field];
            if (typeof va === "string") {
                va = va.toLowerCase();
                vb = (vb || "").toLowerCase();
                return asc ? va.localeCompare(vb) : vb.localeCompare(va);
            }
            va = Number(va) || 0;
            vb = Number(vb) || 0;
            return asc ? va - vb : vb - va;
        });
        return list;
    }

    onUnitChange(ev) {
        this.state.filters.unit_name = ev.target.value;
        this.loadData();
    }

    onPartnerTypeChange(ev) {
        this.state.filters.partner_type = ev.target.value;
        this.loadData();
    }

    onBucketChange(ev) {
        this.state.filters.bucket = ev.target.value;
        this.loadData();
    }

    onComparisonChange(ev) {
        this.state.filters.comparison_type = ev.target.value;
        this.loadData();
    }

    onDatePresetChange(ev) {
        const preset = ev.target.value;
        this.state.datePreset = preset;
        const today = new Date();
        const y = today.getFullYear();
        const m = today.getMonth();

        if (preset === "today") {
            const mm = String(m + 1).padStart(2, '0');
            const dd = String(today.getDate()).padStart(2, '0');
            this.state.filters.as_of_date = `${y}-${mm}-${dd}`;
            this.loadData();
        } else if (preset === "end_of_month") {
            const lastDay = new Date(y, m + 1, 0);
            const mm = String(m + 1).padStart(2, '0');
            const dd = String(lastDay.getDate()).padStart(2, '0');
            this.state.filters.as_of_date = `${y}-${mm}-${dd}`;
            this.loadData();
        } else if (preset === "end_of_last_month") {
            const lastMonthEnd = new Date(y, m, 0);
            const py = lastMonthEnd.getFullYear();
            const pm = String(lastMonthEnd.getMonth() + 1).padStart(2, '0');
            const pd = String(lastMonthEnd.getDate()).padStart(2, '0');
            this.state.filters.as_of_date = `${py}-${pm}-${pd}`;
            this.loadData();
        } else if (preset === "end_of_year") {
            this.state.filters.as_of_date = `${y}-12-31`;
            this.loadData();
        }
    }

    onCustomDateChange(ev) {
        this.state.customAsOfDate = ev.target.value;
        this.state.filters.as_of_date = ev.target.value;
        this.loadData();
    }

    openDocument(item) {
        if (!item) return;
        if (item.source === "education_bill" && item.doc_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "education.bill",
                res_id: item.doc_id,
                views: [[false, "form"]],
                target: "current",
            });
        } else if (item.source === "sif_jurnal" && item.doc_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "sif.jurnal.entry",
                res_id: item.doc_id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    onExportXLSX() {
        const queryParams = new URLSearchParams({
            as_of_date: this.state.filters.as_of_date || "",
            unit_name: this.state.filters.unit_name || "",
            partner_type: this.state.filters.partner_type || "all",
            bucket: this.state.filters.bucket || "all",
            search: this.state.searchQuery || "",
            comparison_type: this.state.filters.comparison_type || "none",
            lang: getActiveLang(),
        });
        window.location.href = `/sif_keuangan/export_aging_piutang_xlsx?${queryParams.toString()}`;
    }
}

registry.category("actions").add("sif_keuangan.AgingPiutangView", AgingPiutangView);
registry.category("actions").add("sif_keuangan.aging_piutang", AgingPiutangView);
