import { Plugin } from "@html_editor/plugin";
import {
    getDeepestPosition,
    isProtected,
    isProtecting,
    isUnprotecting,
} from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { DIRECTIONS } from "@html_editor/utils/position";
import { getCursorDirection } from "@html_editor/utils/selection";
import { _t } from "@web/core/l10n/translation";

export class CollaborationSelectionPlugin extends Plugin {
    static name = "collaboration_selection";
    static dependencies = [
        "history",
        "position",
        "collaboration",
        "collaboration_odoo",
        "local-overlay",
    ];
    resources = {
        handleCollaborationNotification: this.handleCollaborationNotification.bind(this),
        getCollaborationPeerMetadata: () => ({ selectionColor: this.selectionColor }),
        layoutGeometryChange: this.refreshSelection.bind(this),
        collaborativeSelectionUpdate: this.updateSelection.bind(this),
    };
    selectionInfos = new Map();

    setup() {
        this.selectionOverlay = this.shared.makeLocalOverlay("oe-selections-container");
        this.selectionColor = `hsl(${(Math.random() * 360).toFixed(0)}, 75%, 50%)`;
    }
    handleCollaborationNotification({ notificationName, notificationPayload }) {
        switch (notificationName) {
            case "ptp_remove":
                this.multiselectionRemove(notificationPayload);
                this.selectionInfos.delete(notificationPayload);
                break;
        }
    }
    /**
     * @param {import("./collaboration_odoo_plugin").CollaborationSelection} selection
     */
    updateSelection(selection) {
        this.selectionInfos.set(selection.peerId, selection);
        this.drawPeerSelection(selection);
    }
    /**
     * @param {import("./collaboration_odoo_plugin").CollaborationSelection} selection
     */
    drawPeerSelection({ selection, peerId }) {
        const { selectionColor, peerName = _t("Anonymous") } = this.shared.getPeerMetadata(peerId);
        this.multiselectionRemove(peerId);
        let clientRects;

        let anchorNode = this.shared.getNodeById(selection.anchorNodeId);
        let focusNode = this.shared.getNodeById(selection.focusNodeId);
        let anchorOffset = selection.anchorOffset;
        let focusOffset = selection.focusOffset;
        if (!anchorNode || !focusNode) {
            anchorNode = this.editable.children[0];
            focusNode = this.editable.children[0];
            anchorOffset = 0;
            focusOffset = 0;
        }
        const anchorTarget = childNodes(anchorNode).at(anchorOffset);
        const focusTarget = childNodes(focusNode).at(focusOffset);
        const protectionCheck = (node) =>
            isProtecting(node) || (isProtected(node) && !isUnprotecting(node));
        if (protectionCheck(anchorTarget) || protectionCheck(focusTarget)) {
            // TODO @phoenix, TODO ABD: better handle collaborative selection
            // on protected elements.
            return;
        }
        if (anchorNode.isConnected && focusNode.isConnected) {
            [anchorNode, anchorOffset] = getDeepestPosition(anchorNode, anchorOffset);
            [focusNode, focusOffset] = getDeepestPosition(focusNode, focusOffset);
        } else {
            // todo: We should not be able to get here, this fixes multiples
            // issues where we temporarily try to draw a an impossible
            // selection. We should investigate the root cause of this issue.
            anchorNode = this.editable.children[0];
            focusNode = this.editable.children[0];
            anchorOffset = 0;
            focusOffset = 0;
        }

        const direction = getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset);
        const range = new Range();
        try {
            if (direction === DIRECTIONS.RIGHT) {
                range.setStart(anchorNode, anchorOffset);
                range.setEnd(focusNode, focusOffset);
            } else {
                range.setStart(focusNode, focusOffset);
                range.setEnd(anchorNode, anchorOffset);
            }

            clientRects = Array.from(range.getClientRects());
        } catch {
            // Changes in the dom might prevent the range to be instantiated
            // (because of a removed node for example), in which case we ignore
            // the range.
            clientRects = [];
        }
        if (!clientRects.length) {
            return;
        }

        // Draw rects (in case the selection is not collapsed).
        const containerRect = this.selectionOverlay.getBoundingClientRect();
        const indicators = clientRects.map(({ x, y, width, height }) => {
            const rectElement = this.document.createElement("div");
            rectElement.style = `
                position: absolute;
                top: ${y - containerRect.y}px;
                left: ${x - containerRect.x}px;
                width: ${width}px;
                height: ${height}px;
                background-color: ${selectionColor};
                opacity: 0.25;
                pointer-events: none;
            `;
            rectElement.setAttribute("data-selection-peer-id", peerId);
            return rectElement;
        });

        // Draw carret.
        const caretElement = this.document.createElement("div");
        caretElement.style = `border-left: 2px solid ${selectionColor}; position: absolute;`;
        caretElement.setAttribute("data-selection-peer-id", peerId);
        caretElement.className = "oe-collaboration-caret";

        // Draw carret top square.
        const caretTopSquare = this.document.createElement("div");
        caretTopSquare.className = "oe-collaboration-caret-top-square";
        caretTopSquare.style["background-color"] = selectionColor;
        caretTopSquare.setAttribute("data-peer-name", peerName);
        caretElement.append(caretTopSquare);

        if (direction === DIRECTIONS.LEFT) {
            const rect = clientRects[0];
            caretElement.style.height = `${rect.height * 1.2}px`;
            caretElement.style.top = `${rect.y - containerRect.y}px`;
            caretElement.style.left = `${rect.x - containerRect.x}px`;
        } else {
            const rect = clientRects.at(-1);
            caretElement.style.height = `${rect.height * 1.2}px`;
            caretElement.style.top = `${rect.y - containerRect.y}px`;
            caretElement.style.left = `${rect.right - containerRect.x}px`;
        }
        this.selectionOverlay.append(caretElement, ...indicators);
    }

    multiselectionRemove(peerId) {
        const elements = this.selectionOverlay.querySelectorAll(
            `[data-selection-peer-id="${peerId}"]`
        );
        for (const element of elements) {
            element.remove();
        }
    }
    refreshSelection() {
        this.selectionOverlay.replaceChildren();
        for (const selection of this.selectionInfos.values()) {
            this.drawPeerSelection(selection);
        }
    }
}
