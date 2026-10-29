import { _t } from "@web/core/l10n/translation";
import { cookie } from "@web/core/browser/cookie";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { standardFieldProps } from "../standard_field_props";
import { formatJson } from "@web/views/fields/formatters";

import { Component, proxy, useEffect, useProps } from "@odoo/owl";

/**
 * Locates a JSON.parse error in the parsed text. Browsers don't share the same
 * error messages, so the location is extracted from the known formats:
 *  - "... (line 3 column 5)" / "... at line 3 column 5 of the JSON data"
 *  - "... at position 42"
 *  - "Unexpected end of JSON input" / "... end of data ..."
 * and falls back on the first line otherwise.
 *
 * @param {Error} error
 * @param {string} text
 * @returns {{ row: number, column: number }} 0-based position
 */
export function getJsonErrorPosition(error, text) {
    const message = error.message || "";
    const lineMatch = message.match(/line (\d+) column (\d+)/);
    if (lineMatch) {
        return { row: Number(lineMatch[1]) - 1, column: Number(lineMatch[2]) - 1 };
    }
    const positionMatch = message.match(/position (\d+)/);
    let index = positionMatch && Number(positionMatch[1]);
    if (index === null && /end of (JSON input|data)/i.test(message)) {
        index = text.trimEnd().length;
    }
    if (index === null) {
        return { row: 0, column: 0 };
    }
    const lines = text.slice(0, index).split("\n");
    return { row: lines.length - 1, column: lines.at(-1).length };
}

/**
 * @param {string[]} lines
 * @param {{ row: number, column: number }} position
 * @returns {{ row: number, column: number } | null} the position of the last
 *  non blank character before the given position
 */
function getPreviousNonBlank(lines, { row, column }) {
    for (let r = row; r >= 0; r--) {
        const trimmed = (r === row ? lines[r].slice(0, column) : lines[r]).trimEnd();
        if (trimmed) {
            return { row: r, column: trimmed.length - 1 };
        }
    }
    return null;
}

/**
 * JSON.parse reports an error where it notices it, which isn't always where
 * the user made it (e.g. a missing comma is reported on the next property).
 * Returns a user friendly description of the error, located where it most
 * likely is.
 *
 * @param {Error} error the error thrown by JSON.parse
 * @param {string} text the parsed text
 * @returns {{ row: number, column: number, text: string }} 0-based position
 */
export function describeJsonError(error, text) {
    const lines = text.split("\n");
    const position = getJsonErrorPosition(error, text);
    const char = lines[position.row]?.[position.column];
    if (/expected ',' or/i.test(error.message) && char && char !== "}" && char !== "]") {
        const isLineStart = !lines[position.row].slice(0, position.column).trim();
        const previous = isLineStart && getPreviousNonBlank(lines, position);
        const { row, column } = previous ? { ...previous, column: previous.column + 1 } : position;
        return { row, column, text: String(_t("Missing comma")) };
    }
    // the position is already displayed, remove it from the browser message
    const message = error.message
        .replace(/ in JSON at position \d+( \(line \d+ column \d+\))?/, "")
        .replace(/ at line \d+ column \d+ of the JSON data/, "");
    return { ...position, text: message };
}

/**
 * Trailing commas aren't valid JSON, but are a common mistake when editing it
 * by hand: they are ignored. They are replaced by a space, so that the parsing
 * errors positions still match the edited text.
 *
 * @param {string} text
 * @returns {string}
 */
export function removeTrailingCommas(text) {
    return text.replace(/("(?:[^"\\]|\\.)*")|,(?=\s*[\]}])/g, (match, string) => string ?? " ");
}

export class JsonField extends Component {
    static template = "web.JsonField";
    static components = { CodeEditor };
    props = useProps({
        ...standardFieldProps,
    });

    /** Number of spaces used to indent the edited JSON */
    get indent() {
        return 2;
    }
    get maxLines() {
        return 30;
    }

    setup() {
        this.state = proxy({ annotations: [] });
        useEffect(() => {
            const initialValue = this.stringify(this.props.record.data[this.props.name]);
            this.state.initialValue = initialValue;
            // also reset the editor when the record value didn't change (e.g.
            // on discard after an invalid edition, which isn't sent to the record)
            this.state.editorValue = initialValue;
            this.state.annotations = [];
        });
        this.debouncedValidate = useDebounced(() => this.validate(this.editedValue), 300);

        this.isDirty = false;

        const { model } = this.props.record;
        useBus(model.bus, "WILL_SAVE_URGENTLY", () => this.commitChanges());
        useBus(model.bus, "NEED_LOCAL_CHANGES", ({ detail }) =>
            detail.proms.push(this.commitChanges())
        );
    }

    get formattedValue() {
        return formatJson(this.props.record.data[this.props.name]);
    }
    get errorMessage() {
        const [annotation] = this.state.annotations;
        return (
            annotation &&
            _t("Line %(line)s: %(message)s", { line: annotation.row + 1, message: annotation.text })
        );
    }
    get theme() {
        return cookie.get("color_scheme") === "dark" ? "monokai" : "";
    }

    stringify(value) {
        return value === false || value === null || value === undefined
            ? ""
            : JSON.stringify(value, null, this.indent);
    }

    /**
     * @param {string} text
     * @returns {any} the parsed value, false if the text is empty
     * @throws {SyntaxError} if the text isn't valid JSON
     */
    parse(text) {
        return text.trim() ? JSON.parse(removeTrailingCommas(text)) : false;
    }

    /**
     * Displays the parsing error, if any, in the editor gutter.
     *
     * @param {string} text
     * @returns {boolean} whether the text is valid
     */
    validate(text) {
        try {
            this.parse(text);
        } catch (error) {
            const description = describeJsonError(error, removeTrailingCommas(text));
            this.state.annotations = [{ ...description, type: "error" }];
            return false;
        }
        this.state.annotations = [];
        return true;
    }

    handleChange(editedValue) {
        this.editedValue = editedValue;
        this.state.editorValue = editedValue;
        this.isDirty = this.state.initialValue !== editedValue;
        const { record, name } = this.props;
        record.model.bus.trigger("FIELD_IS_DIRTY", this.isDirty);
        if (record.isFieldInvalid(name)) {
            record.resetFieldValidity(name);
        }
        this.debouncedValidate();
    }

    async commitChanges() {
        if (this.props.readonly || !this.isDirty) {
            return;
        }
        this.isDirty = false;
        this.debouncedValidate.cancel();
        const { record, name } = this.props;
        if (!this.validate(this.editedValue)) {
            record.setInvalidField(name);
            return;
        }
        const value = this.parse(this.editedValue);
        // compare the normalized text, as parsed objects are never equal by reference
        if (this.stringify(value) !== this.state.initialValue) {
            await record.update({ [name]: value });
        }
        record.model.bus.trigger("FIELD_IS_DIRTY", false);
    }
}

export const jsonField = {
    component: JsonField,
    displayName: _t("Json"),
    supportedTypes: ["json"],
};

export class ListJsonField extends JsonField {
    static template = "web.ListJsonField";

    get maxLines() {
        return 3;
    }
}

export const listJsonField = {
    ...jsonField,
    component: ListJsonField,
};

registry.category("fields").add("json", jsonField);
registry.category("fields").add("list.json", listJsonField);
