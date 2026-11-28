import { t, useEffect, useProps } from "@odoo/owl";
import { CodeEditor } from "@web/core/code_editor/code_editor";

const T_MARKER = t.object({
    row: t.number(),
    // The number displayed in the marker, if any.
    count: t.number().optional(0),
    // Whether the row can be followed to another place (displayed as an
    // arrow when there is no count).
    target: t.boolean().optional(false),
});
const T_REVEAL_ROW = t.object({
    sessionId: t.or([t.number(), t.string()]),
    row: t.number(),
});

/**
 * Extension of CodeEditor which can display interactive markers in the gutter
 * of some rows, as Ace gutter decorations.
 */
export class CodeEditorWithGutterMarkers extends CodeEditor {
    markerProps = useProps({
        // At most one marker per row. `null` removes the current markers, as
        // Ace does not move them along with their row.
        markers: t.or([t.array(T_MARKER), t.literal(null)]).optional(),
        // Called with the row of the clicked marker and its gutter cell.
        onMarkerClick: t.function().optional(),
        // A row to scroll to, move the cursor to and highlight briefly, once
        // the session is displayed. Give a new object to reveal a row again.
        revealRow: t.or([T_REVEAL_ROW, t.literal(null)]).optional(),
    });
    /** @type {WeakMap<Object, Map<number, string>>} Ace session -> its marked
     *  rows, each with the classes of its marker (one gutter decoration) */
    markedRowsPerSession = new WeakMap();
    lastRevealedRow = null;

    setup() {
        super.setup();

        useEffect(() => {
            // Update the gutter markers and move to a target row if
            // `revealRow` is set.
            const aceEditor = this.aceEditor;
            const value = this.props.value;
            const markers = this.markerProps.markers;
            const revealRow = this.markerProps.revealRow;
            const sessionId = this.props.sessionId;
            if (!aceEditor) {
                return;
            }
            // Run in microtask to be sure that the new editor session is in
            // place before actually updating the markers.
            let cancelled = false;
            queueMicrotask(() => {
                if (!cancelled) {
                    const session = aceEditor.getSession();
                    this.updateMarkers(session, value, markers);
                    if (
                        revealRow &&
                        revealRow !== this.lastRevealedRow &&
                        revealRow.sessionId === sessionId
                    ) {
                        this.lastRevealedRow = revealRow;
                        this.revealRow(session, revealRow.row);
                    }
                }
            });
            return () => {
                cancelled = true;
            };
        });

        useEffect(() => {
            // Register the click handler on gutter elements. The effect only
            // depends on the aceEditor signal.
            const aceEditor = this.aceEditor;
            if (!aceEditor) {
                return;
            }
            const onGutterMouseDown = (ev) => {
                const cellEl = ev.domEvent.target.closest(".ace_gutter-cell");
                if (!cellEl || ev.domEvent.target.closest(".ace_fold-widget")) {
                    return;
                }
                const row = ev.getDocumentPosition().row;
                const currentSession = aceEditor.getSession();
                if (this.markedRowsPerSession.get(currentSession)?.has(row)) {
                    // Skip the default behavior (line select on gutter click)
                    ev.stop();
                    this.markerProps.onMarkerClick?.(row, cellEl);
                }
            };
            aceEditor.on("guttermousedown", onGutterMouseDown);
            return () => aceEditor.off("guttermousedown", onGutterMouseDown);
        });
    }

    /**
     * @param {Object} session the Ace session to display the markers in
     * @param {string} value the value the markers were computed for
     * @param {typeof T_MARKER[]|null|undefined} markers
     */
    updateMarkers(session, value, markers) {
        // Remove the existing gutter decorations and render the new ones in
        // their new locations (Ace does not move decorations automatically
        // when lines are added or removed).
        if (session.getValue() !== value) {
            return;
        }
        for (const [row, classes] of this.markedRowsPerSession.get(session) || []) {
            session.removeGutterDecoration(row, classes);
        }
        const rows = new Map();
        for (const { row, count, target } of markers || []) {
            if (row >= session.getLength() || (!count && !target)) {
                continue;
            }
            // The CSS shows the counts above 9 as "9+".
            const className = count
                ? `o_gutter_marker_${Math.min(count, 10)}`
                : "o_gutter_marker_target";
            const classes = `o_gutter_marker ${className}`;
            session.addGutterDecoration(row, classes);
            rows.set(row, classes);
        }
        this.markedRowsPerSession.set(session, rows);
    }

    /**
     * Moves the cursor to the start of the row, scrolls the row to the middle
     * of the editor and highlights it during 1.5 seconds. Does
     * nothing if the row is out of the session.
     *
     * @param {Object} session the Ace session that is displayed
     * @param {number} row the 0-based row to reveal
     */
    revealRow(session, row) {
        if (row >= session.getLength()) {
            return;
        }
        this.setCursorPosition({ row, column: 0 });
        const markerId = session.addMarker(
            new window.ace.Range(row, 0, row, Infinity),
            "o_revealed_row",
            "fullLine"
        );
        setTimeout(() => session.removeMarker(markerId), 1500);
    }
}
