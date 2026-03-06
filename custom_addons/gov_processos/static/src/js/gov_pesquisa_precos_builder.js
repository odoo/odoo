/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

const BUILDER_SELECTOR = "[data-gov-pesquisa-builder='1'], .gov-pesquisa-builder";
const DEFAULT_COLUMNS = ["Item", "Especificacao", "Unidade", "Quantidade"];

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

function parseNumber(value) {
    const normalized = String(value ?? "").replace(/\./g, "").replace(",", ".").trim();
    const parsed = Number.parseFloat(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
}

function formatNumber(value) {
    return (Number(value) || 0).toLocaleString("pt-BR", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    });
}

function buildDefaultTable() {
    return {
        name: "Tabela 1",
        columns: [...DEFAULT_COLUMNS],
        rows: [["", "", "", ""]],
    };
}

function serializeTablesToMarkup(tables) {
    const chunks = [];
    tables.forEach((table, idx) => {
        const tableName = table.name || `Tabela ${idx + 1}`;
        chunks.push(`### Tabela: ${tableName}`);
        chunks.push(`| ${table.columns.join(" | ")} |`);
        chunks.push(`| ${table.columns.map(() => "---").join(" | ")} |`);
        for (const row of table.rows) {
            const cells = table.columns.map((_, colIdx) => row[colIdx] || "");
            chunks.push(`| ${cells.join(" | ")} |`);
        }
        chunks.push("");
    });
    return chunks.join("\n").trim();
}

function parseMarkupToTables(markup) {
    const source = (markup || "").trim();
    if (!source) {
        return [buildDefaultTable()];
    }

    const lines = source.split(/\r?\n/);
    const tables = [];
    let i = 0;
    while (i < lines.length) {
        const raw = (lines[i] || "").trim();
        if (!raw) {
            i += 1;
            continue;
        }
        let tableName = `Tabela ${tables.length + 1}`;
        if (raw.startsWith("### Tabela:")) {
            tableName = raw.slice("### Tabela:".length).trim() || tableName;
            i += 1;
        }
        if (i >= lines.length) {
            break;
        }

        const headerLine = (lines[i] || "").trim();
        const sepLine = (lines[i + 1] || "").trim();
        if (!(headerLine.startsWith("|") && headerLine.endsWith("|") && sepLine.startsWith("|"))) {
            i += 1;
            continue;
        }
        const columns = headerLine
            .slice(1, -1)
            .split("|")
            .map((part) => part.trim() || "Coluna");
        i += 2;

        const rows = [];
        while (i < lines.length) {
            const line = (lines[i] || "").trim();
            if (!line || !line.startsWith("|") || !line.endsWith("|")) {
                break;
            }
            const cells = line
                .slice(1, -1)
                .split("|")
                .map((part) => part.trim());
            while (cells.length < columns.length) {
                cells.push("");
            }
            rows.push(cells.slice(0, columns.length));
            i += 1;
        }

        tables.push({
            name: tableName,
            columns: columns.length ? columns : [...DEFAULT_COLUMNS],
            rows: rows.length ? rows : [new Array(columns.length || DEFAULT_COLUMNS.length).fill("")],
        });
    }
    return tables.length ? tables : [buildDefaultTable()];
}

function serializeTablesToHtml(tables) {
    const parts = [];
    for (const table of tables) {
        const name = escapeHtml(table.name || "Tabela");
        parts.push(`<h4>${name}</h4>`);
        parts.push("<table class='table table-sm table-bordered gov-pp-rendered'><thead><tr>");
        for (const col of table.columns) {
            parts.push(`<th>${escapeHtml(col)}</th>`);
        }
        parts.push("</tr></thead><tbody>");
        for (const row of table.rows) {
            parts.push("<tr>");
            for (let i = 0; i < table.columns.length; i++) {
                parts.push(`<td>${escapeHtml(row[i] || "")}</td>`);
            }
            parts.push("</tr>");
        }
        parts.push("</tbody></table>");
    }
    return parts.join("");
}

function parseHtmlToTables(htmlValue) {
    const source = (htmlValue || "").trim();
    if (!source) {
        return [buildDefaultTable()];
    }
    const wrapper = document.createElement("div");
    wrapper.innerHTML = source;
    const tables = [];
    wrapper.querySelectorAll("table").forEach((tableEl, idx) => {
        const titleEl = tableEl.previousElementSibling;
        const name =
            titleEl && /^h[1-6]$/i.test(titleEl.tagName)
                ? titleEl.textContent.trim() || `Tabela ${idx + 1}`
                : `Tabela ${idx + 1}`;
        const headerCells = tableEl.querySelectorAll("thead th");
        const columns = headerCells.length
            ? Array.from(headerCells).map((el) => (el.textContent || "").trim() || "Coluna")
            : [...DEFAULT_COLUMNS];
        const rows = [];
        tableEl.querySelectorAll("tbody tr").forEach((rowEl) => {
            const cells = Array.from(rowEl.querySelectorAll("td")).map((el) => (el.textContent || "").trim());
            while (cells.length < columns.length) {
                cells.push("");
            }
            rows.push(cells.slice(0, columns.length));
        });
        tables.push({
            name,
            columns,
            rows: rows.length ? rows : [new Array(columns.length).fill("")],
        });
    });
    return tables.length ? tables : [buildDefaultTable()];
}

function computeStats(table) {
    const quantityCol = table.columns.findIndex((col) => /quantidade|qtd/i.test(col || ""));
    const unitValueCol = table.columns.findIndex((col) => /valor.*unit/i.test(col || ""));
    const totalValueCol = table.columns.findIndex((col) => /valor.*total/i.test(col || ""));
    let quantitySum = 0;
    for (const row of table.rows) {
        if (quantityCol >= 0) {
            quantitySum += parseNumber(row[quantityCol] || 0);
        }
        if (quantityCol >= 0 && unitValueCol >= 0 && totalValueCol >= 0) {
            const computed = parseNumber(row[quantityCol]) * parseNumber(row[unitValueCol]);
            if (computed > 0) {
                row[totalValueCol] = formatNumber(computed);
            }
        }
    }
    return { quantitySum };
}

function normalizeRows(table) {
    table.rows = table.rows.map((row) => {
        const copy = [...row];
        while (copy.length < table.columns.length) {
            copy.push("");
        }
        return copy.slice(0, table.columns.length);
    });
}

function findHtmlInput(root, builderRoot) {
    const localContainer =
        builderRoot.closest(".o_notebook_page") ||
        builderRoot.closest(".tab-pane") ||
        builderRoot.parentElement;
    const localInput =
        localContainer?.querySelector("textarea[name='pesquisa_precos_html']") ||
        localContainer?.querySelector("input[name='pesquisa_precos_html']") ||
        localContainer?.querySelector(".o_field_widget[name='pesquisa_precos_html'] textarea") ||
        localContainer?.querySelector(".o_field_widget[data-name='pesquisa_precos_html'] textarea") ||
        localContainer?.querySelector(".o_field_widget[name='pesquisa_precos_html'] input") ||
        localContainer?.querySelector(".o_field_widget[data-name='pesquisa_precos_html'] input");
    if (localInput) {
        return localInput;
    }
    const globalInput = (
        root.querySelector("textarea[name='pesquisa_precos_html']") ||
        root.querySelector("input[name='pesquisa_precos_html']") ||
        root.querySelector(".o_field_widget[name='pesquisa_precos_html'] textarea") ||
        root.querySelector(".o_field_widget[data-name='pesquisa_precos_html'] textarea") ||
        root.querySelector(".o_field_widget[name='pesquisa_precos_html'] input") ||
        root.querySelector(".o_field_widget[data-name='pesquisa_precos_html'] input")
    );
    if (globalInput) {
        return globalInput;
    }

    // Final fallback: any field widget for pesquisa_precos_html, even if nested differently.
    const fallbackWidget = root.querySelector(
        ".o_field_widget[name='pesquisa_precos_html'], .o_field_widget[data-name='pesquisa_precos_html']"
    );
    return fallbackWidget?.querySelector("textarea, input") || null;
}

function syncHtmlField(state) {
    state.syncing = true;
    state.htmlInput.value = serializeTablesToHtml(state.tables);
    state.htmlInput.dispatchEvent(new Event("input", { bubbles: true }));
    state.htmlInput.dispatchEvent(new Event("change", { bubbles: true }));
    state.syncing = false;
}

function renderBuilderUI(builderRoot, state) {
    const activeTable = state.tables[state.activeIndex] || state.tables[0];
    const stats = computeStats(activeTable);
    const tableOptions = state.tables
        .map((table, idx) => {
            const selected = idx === state.activeIndex ? "selected" : "";
            return `<option value="${idx}" ${selected}>${escapeHtml(table.name || `Tabela ${idx + 1}`)}</option>`;
        })
        .join("");
    const headers = activeTable.columns
        .map(
            (col, colIdx) =>
                `<th><input type="text" class="gov-pp-header-input" data-col="${colIdx}" value="${escapeHtml(col)}"/></th>`
        )
        .join("");
    const bodyRows = activeTable.rows
        .map((row, rowIdx) => {
            const cells = activeTable.columns
                .map((_, colIdx) => {
                    const val = row[colIdx] || "";
                    return `<td><input type="text" class="gov-pp-cell-input" data-row="${rowIdx}" data-col="${colIdx}" value="${escapeHtml(val)}"/></td>`;
                })
                .join("");
            return `<tr>${cells}</tr>`;
        })
        .join("");

    builderRoot.innerHTML = `
        <div class="gov-pp-toolbar">
            <label>Tabela</label>
            <select class="gov-pp-table-select">${tableOptions}</select>
            <button type="button" class="btn btn-secondary btn-sm" data-action="add-table">+ Tabela</button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="remove-table">- Tabela</button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="add-col">+ Coluna</button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="remove-col">- Coluna</button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="add-row">+ Linha</button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="remove-row">- Linha</button>
        </div>
        <div class="gov-pp-table-name-wrap">
            <label>Nome da Tabela</label>
            <input type="text" class="gov-pp-table-name" value="${escapeHtml(activeTable.name || "")}"/>
        </div>
        <div class="gov-pp-grid-wrap">
            <table class="table table-sm table-bordered gov-pp-grid">
                <thead><tr>${headers}</tr></thead>
                <tbody>${bodyRows}</tbody>
            </table>
        </div>
        <div class="gov-pp-summary">
            <span><strong>Total de Quantidade:</strong> ${formatNumber(stats.quantitySum)}</span>
        </div>
        <div class="gov-pp-markup-wrap mt-2">
            <label>Markup da Planilha</label>
            <textarea class="gov-pp-markup-textarea" rows="8">${escapeHtml(serializeTablesToMarkup(state.tables))}</textarea>
        </div>
    `;
}

function wireEvents(builderRoot, state) {
    builderRoot.addEventListener("change", (ev) => {
        const target = ev.target;
        const table = state.tables[state.activeIndex];
        if (!table) {
            return;
        }

        if (target.classList.contains("gov-pp-table-select")) {
            state.activeIndex = Number.parseInt(target.value, 10) || 0;
            renderBuilderUI(builderRoot, state);
            return;
        }
        if (target.classList.contains("gov-pp-table-name")) {
            table.name = target.value || `Tabela ${state.activeIndex + 1}`;
        }
        if (target.classList.contains("gov-pp-header-input")) {
            const col = Number.parseInt(target.dataset.col, 10);
            table.columns[col] = target.value || `Coluna ${col + 1}`;
        }
        if (target.classList.contains("gov-pp-cell-input")) {
            const row = Number.parseInt(target.dataset.row, 10);
            const col = Number.parseInt(target.dataset.col, 10);
            table.rows[row][col] = target.value || "";
        }
        if (target.classList.contains("gov-pp-markup-textarea")) {
            state.tables = parseMarkupToTables(target.value);
            state.activeIndex = 0;
        }

        normalizeRows(state.tables[state.activeIndex]);
        syncHtmlField(state);
        renderBuilderUI(builderRoot, state);
    });

    builderRoot.addEventListener("click", (ev) => {
        const action = ev.target.dataset.action;
        if (!action) {
            return;
        }
        const table = state.tables[state.activeIndex];
        if (!table) {
            return;
        }

        if (action === "add-table") {
            state.tables.push(buildDefaultTable());
            state.tables[state.tables.length - 1].name = `Tabela ${state.tables.length}`;
            state.activeIndex = state.tables.length - 1;
        } else if (action === "remove-table") {
            if (state.tables.length <= 1) {
                return;
            }
            state.tables.splice(state.activeIndex, 1);
            state.activeIndex = Math.max(0, state.activeIndex - 1);
        } else if (action === "add-col") {
            const colName = window.prompt("Nome da nova coluna:", `Coluna ${table.columns.length + 1}`);
            table.columns.push(colName || `Coluna ${table.columns.length + 1}`);
            table.rows = table.rows.map((row) => [...row, ""]);
        } else if (action === "remove-col") {
            if (table.columns.length <= 1) {
                return;
            }
            table.columns.pop();
            table.rows = table.rows.map((row) => row.slice(0, table.columns.length));
        } else if (action === "add-row") {
            table.rows.push(new Array(table.columns.length).fill(""));
        } else if (action === "remove-row") {
            if (table.rows.length <= 1) {
                return;
            }
            table.rows.pop();
        }

        normalizeRows(state.tables[state.activeIndex]);
        syncHtmlField(state);
        renderBuilderUI(builderRoot, state);
    });
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => this._govInitPesquisaPrecosBuilder());
        onPatched(() => this._govInitPesquisaPrecosBuilder());
    },

    _govInitPesquisaPrecosBuilder() {
        if (!this.el) {
            return;
        }
        const builderRoots = this.el.querySelectorAll(BUILDER_SELECTOR);
        if (!builderRoots.length) {
            return;
        }

        for (const builderRoot of builderRoots) {
            const htmlInput = findHtmlInput(this.el, builderRoot);
            if (!htmlInput) {
                continue;
            }

            if (!builderRoot.dataset.govPpBound) {
                const state = {
                    tables: parseHtmlToTables(htmlInput.value),
                    activeIndex: 0,
                    htmlInput,
                    syncing: false,
                };
                builderRoot.dataset.govPpBound = "1";
                builderRoot.__govPpState = state;
                wireEvents(builderRoot, state);

                htmlInput.addEventListener("input", () => {
                    if (state.syncing) {
                        return;
                    }
                    state.tables = parseHtmlToTables(htmlInput.value);
                    state.activeIndex = Math.min(state.activeIndex, state.tables.length - 1);
                    renderBuilderUI(builderRoot, state);
                });

                if (!(htmlInput.value || "").trim()) {
                    syncHtmlField(state);
                }
                renderBuilderUI(builderRoot, state);
                continue;
            }

            const state = builderRoot.__govPpState;
            if (!state || state.htmlInput !== htmlInput) {
                continue;
            }
            renderBuilderUI(builderRoot, state);
        }
    },
});
