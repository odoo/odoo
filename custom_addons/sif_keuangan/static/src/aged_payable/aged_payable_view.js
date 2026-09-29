/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { translate, getActiveLang } from "../i18n";

export class AgedPayableClientView extends Component {
    static template = "sif_keuangan.AgedPayableClientView";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, "0");
        const dd = String(today.getDate()).padStart(2, "0");
        const initialAsOf = `${yyyy}-${mm}-${dd}`;

        this.state = useState({
            filters: {
                as_of_date: initialAsOf,
                based_on: "due_date",
                period_days: 30,
                target_move: "posted",
                partner_id: false,
                search: "",
                lang: getActiveLang(),
            },
            searchQuery: "",
            unfoldedVendors: {},
            data: null,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    t(key, params) {
        return translate(key, params);
    }

    async loadData() {
        this.state.loading = true;
        try {
            const result = await this.orm.call("sif.aged.payable", "get_aged_payable_data", [
                this.state.filters,
            ]);
            this.state.data = result;

            if (result && result.vendors) {
                result.vendors.forEach((v) => {
                    if (this.state.unfoldedVendors[v.id] === undefined) {
                        this.state.unfoldedVendors[v.id] = true;
                    }
                });
            }
        } catch (e) {
            console.error("Error loading Aged Payable data:", e);
            if (this.notification) {
                this.notification.add("Gagal memuat data Aged Payable.", { type: "danger" });
            }
        } finally {
            this.state.loading = false;
        }
    }

    toggleVendor(vendorId) {
        this.state.unfoldedVendors[vendorId] = !this.state.unfoldedVendors[vendorId];
    }

    isVendorUnfolded(vendorId) {
        return this.state.unfoldedVendors[vendorId] !== false;
    }

    unfoldAll() {
        if (this.state.data && this.state.data.vendors) {
            this.state.data.vendors.forEach((v) => {
                this.state.unfoldedVendors[v.id] = true;
            });
        }
    }

    foldAll() {
        if (this.state.data && this.state.data.vendors) {
            this.state.data.vendors.forEach((v) => {
                this.state.unfoldedVendors[v.id] = false;
            });
        }
    }

    async onDateChange(ev) {
        this.state.filters.as_of_date = ev.target.value;
        await this.loadData();
    }

    async onBasedOnChange(ev) {
        this.state.filters.based_on = ev.target.value;
        await this.loadData();
    }

    async onPeriodDaysChange(ev) {
        this.state.filters.period_days = parseInt(ev.target.value, 10);
        await this.loadData();
    }

    async onPartnerChange(ev) {
        const val = ev.target.value;
        this.state.filters.partner_id = val ? parseInt(val, 10) : false;
        await this.loadData();
    }

    async onTargetMoveChange(ev) {
        this.state.filters.target_move = ev.target.value;
        await this.loadData();
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        this.state.filters.search = ev.target.value;
        this.loadData();
    }

    openPPLForm(pplId) {
        if (!pplId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "sifnext.ppl",
            res_id: pplId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onExportPDF() {
        window.print();
    }

    onExportXLSX() {
        const d = this.state.data;
        if (!d || !d.vendors) return;

        const h = d.headers;
        const rows = [
            ['Rekanan', 'Faktur / PPL', 'Invoice Date', 'At Date', h.b1, h.b2, h.b3, h.b4, h.older, 'Total'],
        ];

        d.vendors.forEach(v => {
            rows.push([v.name, '', '', v.total_current_fmt, v.total_b1_fmt, v.total_b2_fmt, v.total_b3_fmt, v.total_b4_fmt, v.total_older_fmt, v.total_grand_fmt]);
            v.lines.forEach(l => {
                rows.push(['', l.name, l.invoice_date_display, l.current_amount_fmt, l.b1_fmt, l.b2_fmt, l.b3_fmt, l.b4_fmt, l.older_fmt, l.total_amount_fmt]);
            });
            rows.push(['Total ' + v.name, '', '', v.total_current_fmt, v.total_b1_fmt, v.total_b2_fmt, v.total_b3_fmt, v.total_b4_fmt, v.total_older_fmt, v.total_grand_fmt]);
        });

        rows.push(['Total Aged Payable', '', '', d.grand_totals.current_fmt, d.grand_totals.b1_fmt, d.grand_totals.b2_fmt, d.grand_totals.b3_fmt, d.grand_totals.b4_fmt, d.grand_totals.older_fmt, d.grand_totals.total_fmt]);

        const csvContent = rows.map(r => r.map(c => `"${(c || '').toString().replace(/"/g, '""')}"`).join(',')).join('\n');
        const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Aged_Payable_${d.as_of_date}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

registry.category("actions").add("sif_keuangan.aged_payable", AgedPayableClientView);
