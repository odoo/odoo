/** @odoo-module native */
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class SurveyCrossTabulation extends Interaction {
    static selector = ".o_survey_cross_tabulation";

    dynamicContent = {
        ".o_survey_cross_tab_btn": { "t-on-click": this.onGenerateClick },
    };

    async onGenerateClick(ev) {
        const btn = ev.currentTarget;
        const surveyId = parseInt(btn.dataset.surveyId);
        const container = this.el.querySelector("#crossTabResult");
        const rowSelect = this.el.querySelector("#crossTabRowQuestion");
        const colSelect = this.el.querySelector("#crossTabColQuestion");

        const rowId = parseInt(rowSelect.value);
        const colId = parseInt(colSelect.value);

        if (!rowId || !colId || rowId === colId) {
            container.innerHTML =
                '<div class="alert alert-warning">Please select two different questions.</div>';
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"/> Loading...';

        try {
            const data = await rpc(`/survey/results/${surveyId}/cross_tabulation`, {
                question_row_id: rowId,
                question_col_id: colId,
            });

            if (data.error) {
                container.innerHTML = `<div class="alert alert-danger">${this._escapeHtml(String(data.error))}</div>`;
                return;
            }

            container.innerHTML = this._renderTable(data);
        } catch {
            container.innerHTML =
                '<div class="alert alert-danger">Failed to load cross-tabulation data.</div>';
        } finally {
            btn.disabled = false;
            btn.innerHTML = "Generate";
        }
    }

    _renderTable(data) {
        if (!data.row_labels.length || !data.col_labels.length) {
            return '<div class="alert alert-info">No overlapping responses found for these questions.</div>';
        }

        let html = `<div class="table-responsive">
            <table class="table table-bordered table-sm">
            <caption class="caption-top text-muted">
                Rows: <strong>${this._escapeHtml(String(data.question_row.title))}</strong> &times;
                Columns: <strong>${this._escapeHtml(String(data.question_col.title))}</strong>
                &mdash; ${data.grand_total} responses
            </caption>
            <thead class="table-light">
                <tr>
                    <th></th>`;

        for (const col of data.col_labels) {
            html += `<th class="text-center">${this._escapeHtml(String(col))}</th>`;
        }
        html += `<th class="text-center table-secondary">Total</th></tr></thead><tbody>`;

        for (let r = 0; r < data.row_labels.length; r++) {
            html += `<tr><th>${this._escapeHtml(String(data.row_labels[r]))}</th>`;
            for (let c = 0; c < data.col_labels.length; c++) {
                const count = data.matrix[r][c];
                const pct =
                    data.grand_total > 0
                        ? ((count / data.grand_total) * 100).toFixed(1)
                        : "0.0";
                const intensity = data.grand_total > 0 ? count / data.grand_total : 0;
                const bg = `rgba(113, 75, 234, ${Math.min(intensity * 3, 0.6)})`;
                html += `<td class="text-center" style="background-color: ${bg}">
                    ${count} <small class="text-muted">(${pct}%)</small></td>`;
            }
            html += `<td class="text-center table-secondary fw-bold">${data.row_totals[r]}</td></tr>`;
        }

        html += `</tbody><tfoot class="table-light"><tr><th class="table-secondary">Total</th>`;
        for (const ct of data.col_totals) {
            html += `<th class="text-center">${ct}</th>`;
        }
        html += `<th class="text-center table-secondary fw-bold">${data.grand_total}</th>`;
        html += `</tr></tfoot></table></div>`;

        return html;
    }

    _escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
}

registry
    .category("public.interactions")
    .add("survey.cross_tabulation", SurveyCrossTabulation);
