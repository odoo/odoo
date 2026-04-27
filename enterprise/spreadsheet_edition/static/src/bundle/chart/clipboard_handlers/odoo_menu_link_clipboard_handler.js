import { AbstractFigureClipboardHandler, registries } from "@odoo/o-spreadsheet";
const { clipboardHandlersRegistries } = registries;

class OdooLinkClipboardHandler extends AbstractFigureClipboardHandler {
    copy(data) {
        const sheetId = this.getters.getActiveSheetId();
        const figure = this.getters.getFigure(sheetId, data.figureId);
        if (!figure) {
            throw new Error(`No figure for the given id: ${data.figureId}`);
        }
        if (figure.tag !== "chart") {
            return;
        }
        const odooMenuId = this.getters.getChartOdooMenu(data.figureId);
        if (odooMenuId) {
            return { odooMenuId };
        }
    }
    paste(target, clippedContent, options) {
        if (!target.figureId || !clippedContent.odooMenuId) {
            return;
        }
        const { figureId } = target;
        const { odooMenuId } = clippedContent;
        this.dispatch("LINK_ODOO_MENU_TO_CHART", {
            chartId: figureId,
            odooMenuId: odooMenuId.xmlid || odooMenuId.id,
        });
    }
}

clipboardHandlersRegistries.figureHandlers.add("odoo_menu_link", OdooLinkClipboardHandler);
