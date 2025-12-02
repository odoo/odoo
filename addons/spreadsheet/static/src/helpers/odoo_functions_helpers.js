// @ts-check

/**
 * Extract the data source id (always the first argument) from the function
 * context of the given token.
 * @param {import("@odoo/o-spreadsheet").EnrichedToken} tokenAtCursor
 * @returns {string | undefined}
 */
export function extractDataSourceId(tokenAtCursor) {
    const idAst = tokenAtCursor.functionContext?.args[0];
    if (!idAst || !["STRING", "NUMBER"].includes(idAst.type)) {
        return;
    }
    return idAst.value;
}
