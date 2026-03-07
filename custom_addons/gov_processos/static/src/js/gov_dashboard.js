/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class GovDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            error: null,
            data: null,
            ug_id: null,
            tab: "kpis",
        });

        onWillStart(() => this._carregarDados());
    }

    async _carregarDados() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.orm.call(
                "gov.dashboard",
                "get_dashboard_data",
                [],
                { ug_id: this.state.ug_id }
            );
            this.state.data = data;
            this.state.loading = false;
        } catch (error) {
            this.state.error = `Erro ao carregar dashboard: ${error.message}`;
            this.state.loading = false;
        }
    }

    async onRefresh() {
        await this._carregarDados();
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    setTabKpis() {
        this.setTab("kpis");
    }

    setTabContabil() {
        this.setTab("contabil");
    }

    setTabAlertas() {
        this.setTab("alertas");
    }

    fmt(valor) {
        if (valor == null) {
            return "-";
        }
        return new Intl.NumberFormat("pt-BR", {
            style: "currency",
            currency: "BRL",
        }).format(valor);
    }

    fmtPct(valor) {
        if (valor == null) {
            return "-";
        }
        return `${Number(valor).toFixed(1)}%`;
    }

    fmtInt(valor) {
        if (valor == null) {
            return "0";
        }
        return Number(valor).toLocaleString("pt-BR");
    }

    get alertasLista() {
        const alertas = this.state.data?.alertas;
        if (Array.isArray(alertas)) {
            return alertas;
        }
        if (alertas && typeof alertas === "object") {
            return Object.entries(alertas).map(([key, value]) => ({
                nivel: value > 0 ? "medio" : "baixo",
                titulo: key,
                descricao: `${value || 0}`,
            }));
        }
        return [];
    }

    get svgBarras() {
        const contabil = this.state.data?.contabil;
        if (!contabil || !Array.isArray(contabil.saldo_por_conta) || !contabil.saldo_por_conta.length) {
            return null;
        }

        const contasBase = contabil.saldo_por_conta.slice(0, 6);
        const maxVal = Math.max(...contasBase.map((c) => c.empenhado || 0), 1);
        const barH = 28;
        const gap = 8;
        const paddingLeft = 160;
        const barMaxW = 320;
        const height = contasBase.length * (barH + gap) + 60;
        const width = paddingLeft + barMaxW + 140;

        const contas = contasBase.map((conta, index) => {
            const y = 30 + index * (barH + gap);
            const empenhado = Number(conta.empenhado || 0);
            const estornado = Number(conta.estornado || 0);
            return {
                codigo: conta.codigo || String(index),
                label: (conta.codigo || "").substring(0, 12),
                y,
                wEmp: (empenhado / maxVal) * barMaxW,
                wEst: (estornado / maxVal) * barMaxW,
                liquidoFmt: this.fmt(conta.liquido),
            };
        });

        return { contas, width, height, paddingLeft, barMaxW };
    }

    corAlerta(nivel) {
        const mapa = {
            critico: "#DC2626",
            alto: "#EA580C",
            medio: "#CA8A04",
            baixo: "#16A34A",
        };
        return mapa[nivel] || "#6B7280";
    }

    pctWidth(pct) {
        return `${Math.min(parseFloat(pct) || 0, 100)}%`;
    }

    corPct(pct) {
        const valor = parseFloat(pct) || 0;
        if (valor >= 90) {
            return "#DC2626";
        }
        if (valor >= 70) {
            return "#EA580C";
        }
        if (valor >= 40) {
            return "#1F4E79";
        }
        return "#16A34A";
    }

    riscoProcesso(processo) {
        if (processo?.prazo_vencido) {
            return "critico";
        }
        if (processo?.urgencia) {
            return "alto";
        }
        return "baixo";
    }

    riscoLabel(processo) {
        const risco = this.riscoProcesso(processo);
        if (risco === "critico") {
            return "CRITICO";
        }
        if (risco === "alto") {
            return "ALTO";
        }
        return "BAIXO";
    }

    abrirEmpenhos() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "gov.empenho",
            view_mode: "list,form",
            name: "Notas de Empenho",
        });
    }

    abrirLiquidacoes() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "gov.liquidacao",
            view_mode: "list,form",
            name: "Notas de Liquidacao",
        });
    }

    abrirPagamentos() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "gov.pagamento",
            view_mode: "list,form",
            name: "Ordens de Pagamento",
        });
    }

    abrirProcessos() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "gov.processo",
            view_mode: "list,form",
            name: "Processos",
        });
    }
}

GovDashboard.template = "gov_processos.GovDashboard";

registry.category("actions").add("gov_dashboard_owl", GovDashboard);
