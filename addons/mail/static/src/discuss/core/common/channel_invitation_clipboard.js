export function parseClipboard(clipboardData) {
    if (clipboardData.types.includes("text/html")) {
        const htmlData = parseHtmlClipboard(clipboardData.getData("text/html"));
        if (htmlData !== null) {
            return htmlData;
        }
    }
    if (clipboardData.types.includes("text/plain")) {
        const textData = clipboardData.getData("text/plain");
        return parseTextClipboard(textData);
    }
    return null;
}

/**
 * Parses the text content of the clipboard rows and returns a comma-separated string of non-empty values.
 * @param {string} clipboardDataHtml - The raw HTML content from the clipboard.
 */
export function parseHtmlClipboard(clipboardDataHtml) {
    const tableDiv = document.createElement("div");
    const DOMPurify = window.DOMPurify;
    tableDiv.innerHTML = DOMPurify.sanitize(clipboardDataHtml, {
        ALLOWED_TAGS: ["table", "tr", "td", "th"],
    });
    const tables = tableDiv.querySelectorAll("table");
    if (tables.length !== 1) {
        return null;
    }
    if (tableDiv.textContent.trim() !== tables[0].textContent.trim()) {
        return null;
    }
    let rows = Array.from(tables[0].querySelectorAll("tr"));
    if (rows.length) {
        const firstRowWithHeader = rows[0].querySelectorAll("th").length > 0;
        if (firstRowWithHeader && rows.length < 2) {
            return "";
        }
        rows = rows.slice(firstRowWithHeader ? 1 : 0);
    }
    return rows
        .reduce((acc, row) => {
            const cells = Array.from(row.querySelectorAll("td"));
            const cellTexts = cells
                .map((cell) => cell.textContent.trim())
                .filter((text) => text.length > 0);
            return acc.concat(cellTexts);
        }, [])
        .join(",");
}

/**
 * Parses the text content of the clipboard and returns a comma-separated string of non-empty values.
 * @param {string} clipboardText - The raw text content from the clipboard.
 */
export function parseTextClipboard(clipboardText) {
    return clipboardText
        .split(/\s+/g)
        .filter((s) => s.length)
        .join(",");
}
