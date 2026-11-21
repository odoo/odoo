import { useDomState } from "@html_builder/core/utils";
import { convertValueToUnit } from "@html_builder/utils/utils_css";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { useEnv } from "@web/owl2/utils";

const EPSILON = 0.0001;

/**
 * Tracks, for each CSS variable, whether its value differs from the variable it
 * is derived from, multiplied by `ratio` (1 by default).
 *
 * @param {Object<string, { derivedFrom: string, ratio?: number }>} variables
 * @returns {{ customized: Object<string, boolean> }}
 */
export function useCustomizedVariables(variables) {
    const env = useEnv();
    return useDomState(() => {
        const htmlStyle = getHtmlStyle(env.editor.document);
        const toPx = (variable) =>
            convertValueToUnit(getCSSVariableValue(variable, htmlStyle), "px", htmlStyle);

        const customized = {};
        for (const [variable, { derivedFrom, ratio = 1 }] of Object.entries(variables)) {
            const value = toPx(variable);
            const expectedValue = toPx(derivedFrom) * ratio;
            customized[variable] = Math.abs(value - expectedValue) >= EPSILON;
        }
        return { customized };
    });
}
