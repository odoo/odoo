/** @odoo-module **/
import { useEffect, onMounted } from "@odoo/owl";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import { escapeRegExp } from "@web/core/utils/strings";

export class IrUiViewCodeEditor extends CodeEditor {
    static props = {
        ...this.props,
        record: { type: Object },
    };

    setup() {
        super.setup(...arguments);
        this.markers = [];

        onMounted(() => {
            this.aceEditor.getSession().on("change", () => {
                // Markers have fixed pixel positions, so they get wonky on change.
                this.clearMarkers();
            });
        });

        useEffect(
            (arch, invalid_locators) => {
                if (arch && invalid_locators) {
                    this.highlightInvalidLocators(arch, invalid_locators);
                    return () => this.clearMarkers();
                }
            },
            () => [this.props.value, this.props.record?.data.invalid_locators]
        );
    }

    async highlightInvalidLocators(arch, invalid_locators) {
        const resModel = this.env.model?.config.resModel;
        const resId = this.env.model?.config.resId;
        if (resModel === "ir.ui.view" && resId) {
            const { doc } = this.aceEditor.session;
            for (const spec of invalid_locators) {
                if (spec.broken_hierarchy) {
                    continue
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
                    const startPos = doc.indexToPosition(startIndex);
                    const endPos = doc.indexToPosition(endIndex);
                    if (startPos.row + 1 === sourceline) {
                        const range = new window.ace.Range(
                            startPos.row,
                            startPos.column,
                            endPos.row,
                            endPos.column
                        );
                        this.markers.push(
                            this.aceEditor.session.addMarker(range, "invalid_locator", "text")
                        );
                    }
                }
            }
        }
    }

    clearMarkers() {
        this.markers.forEach((marker) => this.aceEditor.session.removeMarker(marker));
        this.markers = [];
    }
}
