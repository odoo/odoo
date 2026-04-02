/** @odoo-module **/

export const DEFAULT_SLASH_COMMANDS = [
    {
        name: "base-legal",
        label: "/base-legal",
        description: "Reservar um ponto para injeção de artigos da Lei 14.133/2021.",
        placeholderHtml:
            "<p><span class=\"gov-slash-token\">/base-legal</span> <strong>Base legal:</strong> [selecionar artigos da Lei 14.133/2021]</p>",
    },
];

function cloneValue(value) {
    return JSON.parse(JSON.stringify(value));
}

function normalizeText(text) {
    return String(text || "")
        .replace(/\u00a0/g, " ")
        .replace(/\r/g, "")
        .replace(/[ \t]+\n/g, "\n")
        .trim();
}

function escapeTypstString(value) {
    return String(value || "")
        .replace(/\\/g, "\\\\")
        .replace(/"/g, '\\"')
        .replace(/\$/g, "\\$")
        .replace(/\r/g, "")
        .replace(/\n/g, "\\n");
}

function escapeTypstText(value) {
    return normalizeText(value)
        .replace(/\\/g, "\\\\")
        .replace(/#/g, "\\#")
        .replace(/\$/g, "\\$")
        .replace(/\*/g, "\\*")
        .replace(/_/g, "\\_")
        .replace(/{/g, "\\{")
        .replace(/}/g, "\\}")
        .replace(/\[/g, "\\[")
        .replace(/\]/g, "\\]");
}

function inlineNodeToTypst(node) {
    if (!node) {
        return "";
    }
    if (node.nodeType === Node.TEXT_NODE) {
        return escapeTypstText(node.textContent || "");
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return "";
    }
    const tagName = node.tagName.toLowerCase();
    const content = Array.from(node.childNodes)
        .map((child) => inlineNodeToTypst(child))
        .join("");
    if (tagName === "strong" || tagName === "b") {
        return `*${content}*`;
    }
    if (tagName === "em" || tagName === "i") {
        return `_${content}_`;
    }
    if (tagName === "code") {
        return `\`${escapeTypstText(node.textContent || "")}\``;
    }
    if (tagName === "br") {
        return "\n";
    }
    if (tagName === "a") {
        const href = node.getAttribute("href") || "";
        if (!href) {
            return content;
        }
        return `#link("${escapeTypstString(href)}")[${content || escapeTypstText(href)}]`;
    }
    return content;
}

function tableNodeToTypst(tableElement) {
    const rows = Array.from(tableElement.querySelectorAll("tr"));
    if (!rows.length) {
        return "";
    }
    const matrix = rows.map((row) =>
        Array.from(row.children).map((cell) => ({
            tag: cell.tagName.toLowerCase(),
            text: inlineNodeToTypst(cell).trim(),
        }))
    );
    const columnCount = Math.max(...matrix.map((row) => row.length), 1);
    const headerRow = matrix[0].every((cell) => cell.tag === "th") ? matrix[0] : null;
    const bodyRows = headerRow ? matrix.slice(1) : matrix;
    const parts = [
        "#table(",
        `  columns: ${columnCount},`,
        "  stroke: 0.5pt + gray,",
        "  inset: 6pt,",
    ];
    if (headerRow) {
        parts.push(
            `  table.header(${headerRow
                .map((cell) => `[${cell.text || " "}]`)
                .join(", ")}),`
        );
    }
    for (const row of bodyRows) {
        for (let index = 0; index < columnCount; index++) {
            const cell = row[index];
            parts.push(`  [${cell?.text || " "}],`);
        }
    }
    parts.push(")");
    return parts.join("\n");
}

function blockNodeToTypst(node) {
    if (!node) {
        return "";
    }
    if (node.nodeType === Node.TEXT_NODE) {
        return escapeTypstText(node.textContent || "");
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return "";
    }
    const tagName = node.tagName.toLowerCase();
    if (tagName === "p") {
        return inlineNodeToTypst(node).trim();
    }
    if (tagName === "h1" || tagName === "h2" || tagName === "h3") {
        const level = { h1: 1, h2: 2, h3: 3 }[tagName];
        return `#heading(level: ${level})[${inlineNodeToTypst(node).trim()}]`;
    }
    if (tagName === "ul") {
        return Array.from(node.children)
            .filter((item) => item.tagName?.toLowerCase() === "li")
            .map((item) => `- ${inlineNodeToTypst(item).trim()}`)
            .join("\n");
    }
    if (tagName === "ol") {
        return Array.from(node.children)
            .filter((item) => item.tagName?.toLowerCase() === "li")
            .map((item) => `+ ${inlineNodeToTypst(item).trim()}`)
            .join("\n");
    }
    if (tagName === "table") {
        return tableNodeToTypst(node);
    }
    if (tagName === "blockquote") {
        return `#quote(block: true)[${inlineNodeToTypst(node).trim()}]`;
    }
    const text = inlineNodeToTypst(node).trim();
    return text;
}

export function htmlToTypst(html) {
    const source = String(html || "").trim();
    if (!source) {
        return "";
    }
    const parser = new DOMParser();
    const doc = parser.parseFromString(source, "text/html");
    return Array.from(doc.body.childNodes)
        .map((node) => blockNodeToTypst(node))
        .filter(Boolean)
        .join("\n\n");
}

export function parseSummaryRows(lines) {
    const source = normalizeText(lines);
    if (!source) {
        return [];
    }
    return source
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
            const separatorIndex = line.indexOf(":");
            if (separatorIndex === -1) {
                return { label: line, value: "" };
            }
            return {
                label: line.slice(0, separatorIndex).trim(),
                value: line.slice(separatorIndex + 1).trim(),
            };
        });
}

export function getProcessHeaderRows(bindings) {
    return [
        { label: "Processo", value: bindings?.process_number || "" },
        { label: "Objeto / Assunto", value: bindings?.process_subject || "" },
        { label: "Tipo", value: bindings?.process_type_label || "" },
        { label: "Escopo", value: bindings?.process_scope_label || "" },
        { label: "UG", value: bindings?.company_name || "" },
        { label: "Responsável", value: bindings?.responsible_name || "" },
    ].filter((row) => row.value);
}

export function getSummaryRows(block, bindings) {
    const customRows = parseSummaryRows(block?.content?.linhas);
    if (customRows.length) {
        return customRows;
    }
    return cloneValue(bindings?.summary_rows || []);
}

export function resolveBlockContent(block, bindings) {
    const content = cloneValue(block?.content || {});
    const blockType = block?.type || "";
    if (blockType === "titulo") {
        content.titulo = content.titulo || bindings?.doc_type_label || "Documento";
        content.subtitulo = content.subtitulo || bindings?.process_subject || "";
        return content;
    }
    if (blockType === "cabecalho_processo") {
        return {
            rows: getProcessHeaderRows(bindings),
        };
    }
    if (blockType === "objeto") {
        content.html = content.html || `<p>${bindings?.object_text || ""}</p>`;
        return content;
    }
    if (blockType === "justificativa") {
        content.html = content.html || `<p>${bindings?.justification_text || ""}</p>`;
        return content;
    }
    if (blockType === "base_legal") {
        content.html = content.html || `<p>${bindings?.legal_basis_default || ""}</p>`;
        return content;
    }
    if (blockType === "quadro_resumo") {
        content.linhas = content.linhas || bindings?.summary_rows_text || "";
        return content;
    }
    if (blockType === "assinatura") {
        content.nome = content.nome || bindings?.responsible_name || "";
        content.cargo = content.cargo || bindings?.responsible_role || "";
        return content;
    }
    if (blockType === "encaminhamento") {
        content.html = content.html || `<p>${bindings?.routing_default || ""}</p>`;
        return content;
    }
    if (blockType === "texto_livre") {
        content.html = content.html || "<p>Digite aqui o conteúdo...</p>";
        return content;
    }
    return content;
}

function createContextBlock(bindings) {
    return [
        "#let processo = (",
        `  numero: "${escapeTypstString(bindings?.process_number || "")}",`,
        `  assunto: "${escapeTypstString(bindings?.process_subject || "")}",`,
        `  tipo: "${escapeTypstString(bindings?.process_type_label || "")}",`,
        `  escopo: "${escapeTypstString(bindings?.process_scope_label || "")}",`,
        `  ug: "${escapeTypstString(bindings?.company_name || "")}",`,
        `  valor_estimado: "${escapeTypstString(bindings?.estimated_value_label || "")}",`,
        `  area_requisitante: "${escapeTypstString(bindings?.requesting_area || "")}",`,
        `  responsavel: "${escapeTypstString(bindings?.responsible_name || "")}",`,
        `  objeto: "${escapeTypstString(bindings?.object_text || "")}",`,
        `  justificativa: "${escapeTypstString(bindings?.justification_text || "")}",`,
        ")",
    ].join("\n");
}

function renderKeyValueTable(rows, title) {
    if (!rows.length) {
        return "";
    }
    const parts = [];
    if (title) {
        parts.push(`#heading(level: 2)[${escapeTypstText(title)}]`);
    }
    parts.push(
        [
            "#table(",
            "  columns: (32%, 68%),",
            "  stroke: 0.5pt + gray,",
            "  inset: 8pt,",
            ...rows.flatMap((row) => [
                `  [*${escapeTypstText(row.label || "")}*],`,
                `  [${escapeTypstText(row.value || "")}],`,
            ]),
            ")",
        ].join("\n")
    );
    return parts.join("\n\n");
}

function renderTitleBlock(block, bindings) {
    const content = resolveBlockContent(block, bindings);
    const parts = [];
    if (content.titulo) {
        parts.push(`#heading(level: 1)[${escapeTypstText(content.titulo)}]`);
    }
    if (content.subtitulo) {
        parts.push(`#align(center)[_${escapeTypstText(content.subtitulo)}_]`);
    }
    return parts.join("\n\n");
}

function renderHtmlSection(title, html, bindingsFallback = "") {
    const body = htmlToTypst(html || "");
    const parts = [];
    if (title) {
        parts.push(`#heading(level: 2)[${escapeTypstText(title)}]`);
    }
    if (body) {
        parts.push(body);
    } else if (bindingsFallback) {
        parts.push(escapeTypstText(bindingsFallback));
    }
    return parts.join("\n\n");
}

function renderPointsBlock(block, bindings) {
    const content = resolveBlockContent(block, bindings);
    const points = normalizeText(content.texto)
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
    if (!points.length) {
        return "";
    }
    return [
        "#heading(level: 2)[Pontos-Chave]",
        points.map((point) => `- ${escapeTypstText(point)}`).join("\n"),
    ].join("\n\n");
}

function renderSignatureBlock(block, bindings) {
    const content = resolveBlockContent(block, bindings);
    if (!content.nome && !content.cargo) {
        return "";
    }
    return [
        "#v(1.8em)",
        "#align(right)[",
        `  ${escapeTypstText(content.nome || "")}`,
        content.cargo ? `\n  ${escapeTypstText(content.cargo)}` : "",
        "]",
    ]
        .filter(Boolean)
        .join("\n");
}

export function renderBlocksToTypst(blocks, bindings) {
    const sections = (blocks || [])
        .map((block) => {
            if (!block?.type) {
                return "";
            }
            if (block.type === "titulo") {
                return renderTitleBlock(block, bindings);
            }
            if (block.type === "cabecalho_processo") {
                return renderKeyValueTable(getProcessHeaderRows(bindings), "Cabeçalho do Processo");
            }
            if (block.type === "objeto") {
                return renderHtmlSection("Objeto", resolveBlockContent(block, bindings).html, bindings?.object_text);
            }
            if (block.type === "justificativa") {
                return renderHtmlSection(
                    "Justificativa",
                    resolveBlockContent(block, bindings).html,
                    bindings?.justification_text
                );
            }
            if (block.type === "base_legal") {
                return renderHtmlSection(
                    "Base Legal",
                    resolveBlockContent(block, bindings).html,
                    bindings?.legal_basis_default
                );
            }
            if (block.type === "texto_livre") {
                return renderHtmlSection("", resolveBlockContent(block, bindings).html, "");
            }
            if (block.type === "encaminhamento") {
                return renderHtmlSection(
                    "Encaminhamento",
                    resolveBlockContent(block, bindings).html,
                    bindings?.routing_default
                );
            }
            if (block.type === "quadro_resumo") {
                return renderKeyValueTable(getSummaryRows(block, bindings), "Quadro Resumo");
            }
            if (block.type === "pontos_chave") {
                return renderPointsBlock(block, bindings);
            }
            if (block.type === "assinatura") {
                return renderSignatureBlock(block, bindings);
            }
            return "";
        })
        .filter(Boolean);

    return [
        '#set text(lang: "pt-BR")',
        "#set page(margin: (top: 2cm, right: 2cm, bottom: 2cm, left: 2cm))",
        "#set par(justify: true)",
        createContextBlock(bindings || {}),
        ...sections,
    ]
        .filter(Boolean)
        .join("\n\n");
}

export function enrichBlock(block, catalogMap, bindings) {
    const definition = catalogMap.get(block?.type);
    return {
        id:
            block?.id ||
            `block_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        type: block?.type || "",
        label: block?.label || definition?.label || block?.type || "",
        editable:
            typeof block?.editable === "boolean"
                ? block.editable
                : definition?.editable ?? true,
        content: {
            ...(definition?.defaultContent || {}),
            ...(block?.content || {}),
        },
    };
}

export function enrichBlocks(blocks, catalogMap, bindings) {
    return (blocks || [])
        .filter((block) => block?.type)
        .map((block) => enrichBlock(block, catalogMap, bindings));
}

export function createBlockFromDefinition(definition, catalogMap, bindings) {
    return enrichBlock(
        {
            type: definition.type,
            label: definition.label,
            editable: definition.editable,
            content: cloneValue(definition.defaultContent || {}),
        },
        catalogMap,
        bindings
    );
}

export function detectSlashCommand(editorElement) {
    const selection = window.getSelection();
    if (!selection || !selection.rangeCount || !editorElement?.contains(selection.anchorNode)) {
        return null;
    }
    const currentRange = selection.getRangeAt(0).cloneRange();
    const textRange = currentRange.cloneRange();
    textRange.selectNodeContents(editorElement);
    textRange.setEnd(currentRange.endContainer, currentRange.endOffset);
    const textBeforeCaret = textRange.toString();
    const match = textBeforeCaret.match(/(?:^|\s)\/([a-z-]{0,40})$/i);
    if (!match) {
        return null;
    }
    return {
        query: (match[1] || "").toLowerCase(),
        raw: match[0],
    };
}

export function applySlashCommandToHtml(html, command) {
    const source = String(html || "");
    const cleaned = source
        .replace(/(?:&nbsp;|\s)*\/[a-z-]*<\/p>\s*$/i, "</p>")
        .replace(/(?:&nbsp;|\s)*\/[a-z-]*$/i, "")
        .trim();
    const placeholder = command?.placeholderHtml || "";
    if (!cleaned) {
        return placeholder;
    }
    return `${cleaned}${placeholder.startsWith("<") ? "" : " "}${placeholder}`;
}
