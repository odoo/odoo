import { Component, proxy, t, untrack, useListener, useProps } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { Operation } from "@web/model/relational_model/operation";
import { DurationParseError, InvalidNumberError } from "./parsers";

const PREVIEW_PARSE_ERRORS = [EvalError, InvalidNumberError, DurationParseError];

class InputPreviewPopover extends Component {
    static template = "web.InputPreviewPopover";
    props = useProps({
        state: t.object(),
        close: t.function().optional(),
    });
}

/**
 * It displays, in a popover anchored on the input, the value that will be set on
 * the field once the text typed by the user is parsed (e.g. "=2*3" or "+=5"). The popover is only
 * shown if that value differs from the text of the input.
 *
 * @param {Object} params
 * @param {Ref<HTMLInputElement> | (() => HTMLInputElement | null)} params.ref a ref or signal containing the input
 * @param {(value: string) => any} params.parse a function that parses the value of the input
 * @param {() => string} params.getValue a function that returns the current value of the field in
 *  the record
 * @param {(value: any) => string} params.format a function that formats the result of the parsing
 * @param {boolean} [params.onlyFormula] if true, show the preview only when the content is a formula
 *   or an operation
 */
export function useInputPreview(params) {
    const inputRef = params.ref;
    const getEl = () => untrack(inputRef);
    const state = proxy({ formattedResult: "" });
    const popover = usePopover(InputPreviewPopover, { position: "bottom" });

    /**
     * Get the preview value or null if there is nothing to show
     */
    function getPreview(text) {
        let result;
        try {
            result = params.parse(text);
        } catch (error) {
            if (PREVIEW_PARSE_ERRORS.every((e) => !(error instanceof e))) {
                throw error;
            }
            return null;
        }
        if (params.onlyFormula && !(result instanceof Operation) && !text.trim().startsWith("=")) {
            return null;
        }
        if (result instanceof Operation) {
            result = result.compute(params.getValue());
        }
        const formatted = params.format(result);
        return text !== formatted ? formatted : null;
    }

    function updatePreview() {
        const el = getEl();
        const preview = el && el.value ? getPreview(el.value) : null;
        if (!preview) {
            popover.close();
            return;
        }
        state.formattedResult = preview;
        if (!popover.isOpen) {
            popover.open(el, { state });
        }
    }

    useListener(inputRef, "input", updatePreview);
    useListener(inputRef, "focusin", updatePreview);
    useListener(inputRef, "focusout", () => popover.close());
}
