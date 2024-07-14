/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SPREADSHEET_DIMENSIONS } from "@odoo/o-spreadsheet";

/**
 * @returns {Promise<Array>}
 */
export function useSpreadsheetLocales() {
    const orm = useService("orm");
    async function loadLocales() {
        return orm.call("res.lang", "get_locales_for_spreadsheet", []);
    }
    return loadLocales;
}

/**
 * @returns {Promise<Array>}
 */
export function useSpreadsheetCurrencies() {
    const orm = useService("orm");
    async function loadCurrencies() {
        const odooCurrencies = await orm.searchRead(
            "res.currency", // model
            [], // domain
            ["symbol", "full_name", "position", "name", "decimal_places"], // fields
            {
                // opts
                order: "active DESC, full_name ASC",
                context: { active_test: false },
            }
        );
        return odooCurrencies.map((currency) => {
            return {
                code: currency.name,
                symbol: currency.symbol,
                position: currency.position || "after",
                name: currency.full_name || _t("Currency"),
                decimalPlaces: currency.decimal_places || 2,
            };
        });
    }
    return loadCurrencies;
}

/**
 * @returns {String}
 */
export function useSpreadsheetThumbnail() {
    return () => {
        const dimensions = SPREADSHEET_DIMENSIONS;
        const canvas = document.querySelector(".o-grid canvas:not(.o-figure-canvas)");
        const canvasResizer = document.createElement("canvas");
        const size = 750;
        canvasResizer.width = size;
        canvasResizer.height = size;
        const canvasCtx = canvasResizer.getContext("2d");
        // use only 25 first rows in thumbnail
        const sourceSize = Math.min(
            25 * dimensions.DEFAULT_CELL_HEIGHT,
            canvas.width,
            canvas.height
        );
        canvasCtx.drawImage(
            canvas,
            dimensions.HEADER_WIDTH - 1,
            dimensions.HEADER_HEIGHT - 1,
            sourceSize,
            sourceSize,
            0,
            0,
            size,
            size
        );
        return canvasResizer.toDataURL().replace("data:image/png;base64,", "");
    };
}
