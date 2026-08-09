/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

export class DrsDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.trendRef = useRef("trendChart");
        this.shiftRef = useRef("shiftChart");
        this.qualityRef = useRef("qualityChart");
        this.charts = {};
        this.refreshInterval = null;

        this.state = useState({
            initialLoad: true,
            lastUpdated: null,
            filters: { quickRange: "today", dateFrom: "", dateTo: "", machine: "all", shift: "all", supervisorId: "all" },
            supervisorOptions: [],
            kpi: {
                totalWeight: 0, totalRolls: 0, totalLength: 0, avgWeight: 0,
                activeMachines: 0, qualityScore: 100, scrapRate: 0, aiDefects: 0
            },
            trend: [],
            shiftBreakdown: [],
            machineList: [],
            recent: [],
            qualityByZone: [],
            activeAlerts: [], // SAFELY DEFINED TO PREVENT CRASHES
            hasData: false
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.fetchSupervisorOptions();
            await this.fetchDashboardData();
        });

        onMounted(() => {
            this.renderCharts();
            this.refreshInterval = setInterval(() => {
                this.fetchDashboardData();
            }, 15000);
        });

        onWillUnmount(() => {
            if (this.refreshInterval) clearInterval(this.refreshInterval);
            Object.values(this.charts).forEach((c) => c && c.destroy());
        });
    }

    async fetchSupervisorOptions() {
        try {
            const sups = await this.orm.searchRead("hr.employee", [["is_drs_supervisor", "=", true]], ["id", "name"]);
            this.state.supervisorOptions = sups.map(s => ({ id: s.id, name: s.name }));
        } catch (e) {
            this.state.supervisorOptions = [];
        }
    }

    buildDomain() {
        let domain = [];
        if (this.state.filters.quickRange === "today" && !this.state.filters.dateFrom) {
            const today = new Date().toISOString().slice(0, 10);
            domain.push(['date', '=', today]);
        } else {
            if (this.state.filters.dateFrom) domain.push(['date', '>=', this.state.filters.dateFrom]);
            if (this.state.filters.dateTo) domain.push(['date', '<=', this.state.filters.dateTo]);
        }
        if (this.state.filters.machine && this.state.filters.machine !== "all") domain.push(['machine_number', '=', this.state.filters.machine]);
        if (this.state.filters.shift && this.state.filters.shift !== "all") domain.push(['shift', '=', this.state.filters.shift]);
        if (this.state.filters.supervisorId && this.state.filters.supervisorId !== "all") domain.push(['supervisor_id', '=', parseInt(this.state.filters.supervisorId, 10)]);
        return domain;
    }

    async fetchDashboardData() {
        const domain = this.buildDomain();

        const allRecords = await this.orm.searchRead(
            "mrp.drs.production", domain,
            ["final_weight", "length", "machine_number", "shift", "date", "supervisor_id", "output_roll_number"],
            { order: 'date asc, id asc' }
        );

        this.state.hasData = allRecords.length > 0;

        let totalWeight = 0, totalLength = 0;
        const machineData = {};
        const shiftData = {};
        const trendData = {};
        const prodMachineMap = {};

        for (const rec of allRecords) {
            const w = rec.final_weight || 0;
            totalWeight += w;
            totalLength += rec.length || 0;

            prodMachineMap[rec.id] = rec.machine_number;

            if (rec.machine_number) {
                if (!machineData[rec.machine_number]) {
                    machineData[rec.machine_number] = { weight: 0, shift: rec.shift, supervisor: rec.supervisor_id ? rec.supervisor_id[1] : 'Unknown', hasAlert: false };
                }
                machineData[rec.machine_number].weight += w;
                machineData[rec.machine_number].shift = rec.shift;
                machineData[rec.machine_number].supervisor = rec.supervisor_id ? rec.supervisor_id[1] : 'Unknown';
            }

            if (rec.shift) {
                if (!shiftData[rec.shift]) shiftData[rec.shift] = 0;
                shiftData[rec.shift] += w;
            }

            const d = rec.date || "Unknown";
            if (!trendData[d]) trendData[d] = 0;
            trendData[d] += w;
        }

        let qualityScore = 100;
        const alerts = [];
        this.state.qualityByZone = [];

        if (allRecords.length > 0) {
            const recordIds = allRecords.map(r => r.id);
            try {
                const lines = await this.orm.searchRead(
                    "mrp.drs.extrusion.line", [["production_id", "in", recordIds]], ["zone", "set_temperature", "actual_temperature", "production_id"]
                );

                const zoneMap = {};
                let totalAbsDev = 0, devCount = 0;

                for (const l of lines) {
                    if (!l.zone) continue;
                    const setT = l.set_temperature || 0;
                    const actT = l.actual_temperature || 0;

                    if (!zoneMap[l.zone]) zoneMap[l.zone] = { set: 0, actual: 0, n: 0 };
                    zoneMap[l.zone].set += setT;
                    zoneMap[l.zone].actual += actT;
                    zoneMap[l.zone].n += 1;

                    if (setT > 0) {
                        const diff = Math.abs(actT - setT);
                        totalAbsDev += diff;
                        devCount += 1;

                        if (diff >= 15) {
                            const mNum = prodMachineMap[l.production_id[0]];
                            alerts.push(`Critical Temp: M-${mNum} ${l.zone.replace('zone', 'Zone ')} is off by ${Math.round(diff)}°C`);
                            if (machineData[mNum]) machineData[mNum].hasAlert = true;
                        }
                    }
                }

                const zoneOrder = ["zone1", "zone2", "zone3", "zone4", "zone5"];
                this.state.qualityByZone = zoneOrder.filter(z => zoneMap[z]).map(z => ({
                    label: z.replace("zone", "Zone "),
                    setTemp: Math.round((zoneMap[z].set / zoneMap[z].n) * 10) / 10,
                    actualTemp: Math.round((zoneMap[z].actual / zoneMap[z].n) * 10) / 10,
                }));

                if (devCount > 0) {
                    qualityScore = Math.max(0, Math.round(100 - ((totalAbsDev / devCount) / 5) * 100));
                }
            } catch (err) {
                // Extrusion line model optional fallback
            }
        }

        const sumWeight = Math.round(totalWeight * 100) / 100;

        this.state.kpi = {
            totalWeight: sumWeight,
            totalRolls: allRecords.length,
            totalLength: Math.round(totalLength * 100) / 100,
            avgWeight: allRecords.length > 0 ? Math.round((sumWeight / allRecords.length) * 10) / 10 : 0,
            activeMachines: Object.keys(machineData).length,
            qualityScore: qualityScore,
            scrapRate: 0,
            aiDefects: 0
        };

        this.state.activeAlerts = [...new Set(alerts)];

        this.state.machineList = Object.keys(machineData).map(key => ({
            name: key,
            weight: Math.round(machineData[key].weight * 100) / 100,
            shift: machineData[key].shift,
            supervisor: machineData[key].supervisor,
            hasAlert: machineData[key].hasAlert
        }));

        this.state.shiftBreakdown = Object.keys(shiftData).map(key => ({
            label: key === 'first' ? 'First Shift' : 'Second Shift',
            weight: Math.round(shiftData[key] * 100) / 100
        }));

        this.state.trend = Object.keys(trendData).map(date => ({
            label: date,
            weight: Math.round(trendData[date] * 100) / 100
        }));

        this.state.recent = [...allRecords].reverse().slice(0, 5);

        const now = new Date();
        this.state.lastUpdated = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        this.state.initialLoad = false;

        this.renderCharts();
    }

    setQuickRange(range) {
        this.state.filters.quickRange = range;
        const today = new Date().toISOString().slice(0, 10);
        if (range === "today") {
            this.state.filters.dateFrom = ""; this.state.filters.dateTo = "";
        } else if (range === "week") {
            const d = new Date(); d.setDate(d.getDate() - 6);
            this.state.filters.dateFrom = d.toISOString().slice(0, 10); this.state.filters.dateTo = today;
        } else if (range === "month") {
            const d = new Date(); d.setDate(1);
            this.state.filters.dateFrom = d.toISOString().slice(0, 10); this.state.filters.dateTo = today;
        } else {
            this.state.filters.dateFrom = ""; this.state.filters.dateTo = "";
        }
        this.fetchDashboardData();
    }

    onFilterChange(field, ev) {
        this.state.filters[field] = ev.target.value;
        if (field === "dateFrom" || field === "dateTo") this.state.filters.quickRange = "custom";
        this.fetchDashboardData();
    }

    resetFilters() {
        this.state.filters = { quickRange: "today", dateFrom: "", dateTo: "", machine: "all", shift: "all", supervisorId: "all" };
        this.fetchDashboardData();
    }

    renderCharts() {
        if (!window.Chart || !this.state.hasData) return;

        Object.values(this.charts).forEach(c => c && c.destroy());

        if (this.trendRef.el) {
            this.charts.trend = new window.Chart(this.trendRef.el.getContext("2d"), {
                type: "line",
                data: {
                    labels: this.state.trend.map(t => t.label),
                    datasets: [{
                        label: "Output (kg)", data: this.state.trend.map(t => t.weight),
                        borderColor: "#7c3aed", backgroundColor: "rgba(124, 58, 237, 0.08)", fill: true, tension: 0.4
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });
        }

        if (this.shiftRef.el) {
            this.charts.shift = new window.Chart(this.shiftRef.el.getContext("2d"), {
                type: "bar",
                data: {
                    labels: this.state.shiftBreakdown.map(s => s.label),
                    datasets: [{
                        data: this.state.shiftBreakdown.map(s => s.weight),
                        backgroundColor: ["#7c3aed", "#06b6d4"], borderRadius: 6
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });
        }

        if (this.qualityRef.el) {
            this.charts.quality = new window.Chart(this.qualityRef.el.getContext("2d"), {
                type: "bar",
                data: {
                    labels: this.state.qualityByZone.map(z => z.label),
                    datasets: [
                        { label: "Set Temp", data: this.state.qualityByZone.map(z => z.setTemp), backgroundColor: "#cbd5e1" },
                        { label: "Actual Temp", data: this.state.qualityByZone.map(z => z.actualTemp), backgroundColor: "#10b981" }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }
    }

    openFilteredWork(extraDomain, title) {
        this.action.doAction({
            type: "ir.actions.act_window", name: title || "Production Reports", res_model: "mrp.drs.production",
            views: [[false, "list"], [false, "form"]], domain: this.buildDomain().concat(extraDomain || [])
        });
    }

    openRecord(id) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "mrp.drs.production", views: [[false, "form"]], res_id: id });
    }
}
DrsDashboard.template = "mrp_drs_production.DashboardTemplate";
registry.category("actions").add("drs_dashboard_action", DrsDashboard);