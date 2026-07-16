import { props, t, useEffect } from "@odoo/owl";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import { escapeRegExp } from "@web/core/utils/strings";

const T_INVALID_LOCATORS = t.object({
    attrib: t.record(t.string()),
    broken_hierarchy: t.boolean().optional(),
    sourceline: t.number(),
    tag: t.string(),
});

export class IrUiViewCodeEditor extends CodeEditor {
    irUiViewProps = props({
        invalidLocators: t.array(T_INVALID_LOCATORS).optional(),
    });
    markers = [];

    setup() {
        super.setup();

        useEffect(() => {
            if (!this.aceEditor) {
                return;
            }
            // Markers have fixed pixel positions, so they get wonky on change.
            this.aceEditor.getSession().on("change", this.clearMarkers.bind(this));
        });

        useEffect(() => {
            if (!this.aceEditor) {
                return;
            }
            const arch = this.props.value;
            const invalidLocators = this.irUiViewProps.invalidLocators;
            if (arch && invalidLocators) {
                this.highlightInvalidLocators(arch, invalidLocators);
                return this.clearMarkers.bind(this);
            }
        });
    }

    /**
     * @param {string} arch
     * @param {Iterable<typeof T_INVALID_LOCATORS>} invalidLocators
     */
    highlightInvalidLocators(arch, invalidLocators) {
        const session = this.aceEditor.getSession();
        for (const spec of invalidLocators) {
            if (spec.broken_hierarchy) {
                continue;
            }
            const { tag, attrib, sourceline } = spec;
            const attribRegex = Object.entries(attrib)
                .map(([key, value]) => {
                    const escapedValue = escapeRegExp(value).replace(/"/g, '("|&quot;)');
                    return (
                        `(?=[^>]*?\\b${escapeRegExp(key)}\\s*=\\s*` +
                        `(?:"[^"]*${escapedValue}[^"]*"|'[^']*${escapedValue}[^']*'))`
                    );
                })
                .join("");
            const nodeRegex = new RegExp(`<${escapeRegExp(tag)}\\s+${attribRegex}[^>]*>`, "g");
            for (const match of arch.matchAll(nodeRegex)) {
                const startIndex = match.index;
                const endIndex = startIndex + match[0].length;
                const startPos = session.doc.indexToPosition(startIndex);
                const endPos = session.doc.indexToPosition(endIndex);
                if (startPos.row + 1 === sourceline) {
                    const range = new window.ace.Range(
                        startPos.row,
                        startPos.column,
                        endPos.row,
                        endPos.column
                    );
                    this.markers.push(session.addMarker(range, "invalid_locator", "text"));
                }
            }
        }
    }

    clearMarkers() {
        const session = this.aceEditor.getSession();
        this.markers.forEach((marker) => session.removeMarker(marker));
        this.markers = [];
    }
}
