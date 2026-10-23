import { convertValueToUnit } from "@html_builder/utils/utils_css";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { proxy, useListener } from "@odoo/owl";
import { useEnv } from "@web/owl2/utils";

const EPSILON = 0.0001;

export function useVariablesDifferentFromGlobal(variables, doc) {
    const env = useEnv();
    const state = proxy({ variablesDifferentFromGlobal: {} });
    const updateState = () => {
        for (const variable of variables) {
            state.variablesDifferentFromGlobal[variable] = isVariableDifferentFromGlobal(
                variable,
                doc
            );
        }
    };
    updateState();
    useListener(env.editorBus, "DOM_UPDATED", updateState);
    return state;
}

function isVariableDifferentFromGlobal(variable, doc) {
    const htmlStyle = getHtmlStyle(doc);
    const globalVariable = variable.replace(/^(btn|input|card)-/, "");
    const value = convertValueToUnit(getCSSVariableValue(variable, htmlStyle), "rem", htmlStyle);
    const globalValue = convertValueToUnit(
        getCSSVariableValue(globalVariable, htmlStyle),
        "rem",
        htmlStyle
    );
    return Math.abs(value - globalValue) >= EPSILON;
}
