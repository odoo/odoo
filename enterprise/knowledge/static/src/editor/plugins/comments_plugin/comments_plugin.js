import { Plugin } from "@html_editor/plugin";
import { leftPos, rightPos, nodeSize } from "@html_editor/utils/position";
import { renderToElement } from "@web/core/utils/render";
import { CommentBeaconManager } from "@knowledge/comments/comment_beacon_manager";
import { registry } from "@web/core/registry";
import { KnowledgeCommentsHandler } from "@knowledge/comments/comments_handler/comments_handler";
import { _t } from "@web/core/l10n/translation";
import { closestElement, childNodes } from "@html_editor/utils/dom_traversal";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { fillEmpty } from "@html_editor/utils/dom";
import {
    isParagraphRelatedElement,
    isPhrasingContent,
    isContentEditable,
    isZwnbsp,
    isListItemElement,
} from "@html_editor/utils/dom_info";
import { uniqueId } from "@web/core/utils/functions";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";
import { withSequence } from "@html_editor/utils/resource";

export class KnowledgeCommentsPlugin extends Plugin {
    static id = "knowledgeComments";
    static dependencies = [
        "baseContainer",
        "history",
        "dom",
        "protectedNode",
        "selection",
        "position",
        "localOverlay",
        "linkSelection",
        "format",
        "delete",
    ];
    resources = {
        user_commands: [
            {
                id: "addComments",
                icon: "fa-commenting",
                run: this.addCommentToSelection.bind(this),
            },
        ],
        toolbar_groups: [
            withSequence(60, {
                id: "knowledge",
            }),
            withSequence(60, {
                id: "knowledge_image",
                namespace: "image",
            }),
        ],
        toolbar_items: [
            {
                id: "comments",
                groupId: "knowledge",
                commandId: "addComments",
                title: _t("Add a comment to selection"),
                text: _t("Comment"),
                isDisabled: () => !this.canAddCommentToSelection(),
            },
            {
                id: "comments_image",
                groupId: "knowledge_image",
                commandId: "addComments",
                title: _t("Add a comment to an image"),
                text: _t("Comment"),
                isDisabled: () => !this.canAddCommentToSelection(),
            },
        ],

        /** Handlers */
        layout_geometry_change_handlers: () => {
            // TODO ABD: why is this called
            this.commentBeaconManager?.drawThreadOverlays();
            this.config.onLayoutGeometryChange();
        },
        selectionchange_handlers: (selectionData) => {
            if (
                !selectionData.documentSelectionIsInEditable ||
                !selectionData.editableSelection ||
                selectionData.documentSelectionIsProtected ||
                selectionData.documentSelectionIsProtecting
            ) {
                return;
            }
            const editableSelection = selectionData.editableSelection;
            const target =
                editableSelection.anchorNode.nodeType === Node.TEXT_NODE
                    ? editableSelection.anchorNode
                    : childNodes(editableSelection.anchorNode).at(editableSelection.anchorOffset);
            if (!target || !target.isConnected) {
                return;
            }
            this.commentBeaconManager.activateRelatedThread(target);
        },
        restore_savepoint_handlers: this.updateBeacons.bind(this),
        history_reset_handlers: () => this.updateBeacons(),
        history_reset_from_steps_handlers: this.updateBeacons.bind(this),
        step_added_handlers: () => this.commentBeaconManager.drawThreadOverlays(),
        external_step_added_handlers: this.updateBeacons.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.normalize.bind(this),

        /** Overrides */
        // TODO ABD: arbitrary sequence, investigate what makes sense
        delete_forward_overrides: withSequence(1, this.handleDeleteForward.bind(this)),
        delete_backward_overrides: withSequence(1, this.handleDeleteBackward.bind(this)),

        intangible_char_for_keyboard_navigation_predicates: this.arrowShouldSkip.bind(this),
    };

    setup() {
        // ensure that this plugin is not dependent on the collaboration plugin
        this.peerId = this.config.collaboration?.peerId ?? "";
        this.commentsService = this.services["knowledge.comments"];
        this.commentsState = this.commentsService.getCommentsState();
        // reset pending beacons
        let previousActiveThreadId;
        this.alive = true;
        effect(
            batched((state) => {
                if (!this.alive) {
                    return;
                }
                if (previousActiveThreadId === state.activeThreadId) {
                    return;
                }
                if (
                    previousActiveThreadId !== "undefined" &&
                    state.activeThreadId === "undefined"
                ) {
                    this.commentBeaconManager.pendingBeacons = new Set();
                } else if (previousActiveThreadId === "undefined") {
                    this.commentBeaconManager.sortThreads();
                    if (this.commentBeaconManager.bogusBeacons.size) {
                        this.commentBeaconManager.removeBogusBeacons();
                        this.dependencies.history.addStep();
                    }
                    this.commentBeaconManager.drawThreadOverlays();
                }
                previousActiveThreadId = state.activeThreadId;
            }),
            [this.commentsState]
        );
        this.localOverlay =
            this.dependencies.localOverlay.makeLocalOverlay("KnowledgeThreadBeacons");
        this.commentBeaconManager = new CommentBeaconManager({
            document: this.document,
            source: this.editable,
            overlayContainer: this.localOverlay,
            commentsState: this.commentsState,
            peerId: this.peerId,
            removeBeacon: this.removeBeacon.bind(this),
            setSelection: this.dependencies.selection.setSelection,
            onStep: () => {
                this.dependencies.history.addStep();
            },
        });
        this.addDomListener(window, "click", this.onWindowClick.bind(this));
        this.overlayComponentsKey = uniqueId("KnowledgeCommentsHandler");
        registry.category(this.config.localOverlayContainers.key).add(
            this.overlayComponentsKey,
            {
                Component: KnowledgeCommentsHandler,
                props: {
                    commentBeaconManager: this.commentBeaconManager,
                    contentRef: {
                        el: this.editable,
                    },
                },
            },
            { force: true }
        );
    }

    arrowShouldSkip(ev, char, lastSkipped) {
        if (char !== undefined || lastSkipped !== "\uFEFF") {
            return;
        }
        const selection = this.document.getSelection();
        if (!selection) {
            return;
        }
        const { anchorNode, focusNode } = selection;
        if (
            !this.editable.contains(anchorNode) ||
            (focusNode !== anchorNode && !this.editable.contains(focusNode))
        ) {
            return;
        }
        const screenDirection = ev.key === "ArrowLeft" ? "left" : "right";
        const isRtl = closestElement(focusNode, "[dir]")?.dir === "rtl";
        const domDirection = (screenDirection === "left") ^ isRtl ? "previous" : "next";
        let targetNode;
        let targetOffset;
        const range = selection.getRangeAt(0);
        if (ev.shiftKey) {
            targetNode = selection.focusNode;
            targetOffset = selection.focusOffset;
        } else {
            if (domDirection === "previous") {
                targetNode = range.startContainer;
                targetOffset = range.startOffset;
            } else {
                targetNode = range.endContainer;
                targetOffset = range.endOffset;
            }
        }
        if (domDirection === "previous") {
            const beacon = this.identifyPreviousBeacon({
                endContainer: targetNode,
                endOffset: targetOffset,
            });
            return beacon && this.commentBeaconManager.isDisabled(beacon);
        } else {
            const beacon = this.identifyNextBeacon({
                startContainer: targetNode,
                startOffset: targetOffset,
            });
            return beacon && this.commentBeaconManager.isDisabled(beacon);
        }
    }

    identifyNextBeacon(range) {
        const { startContainer, startOffset } = range;
        if (startContainer.nodeType !== Node.TEXT_NODE) {
            return;
        }
        let container;
        if (isZwnbsp(startContainer)) {
            container = startContainer;
        } else if (
            startOffset === nodeSize(startContainer) &&
            startContainer.nextSibling?.nodeType === Node.TEXT_NODE &&
            isZwnbsp(startContainer.nextSibling)
        ) {
            container = startContainer.nextSibling;
        }
        if (container) {
            const [anchorNode, anchorOffset] = rightPos(container);
            const target = childNodes(anchorNode).at(anchorOffset);
            if (target?.matches?.(".oe_thread_beacon")) {
                return target;
            }
        }
    }

    identifyPreviousBeacon(range) {
        const { endContainer, endOffset } = range;
        if (endContainer.nodeType !== Node.TEXT_NODE) {
            return;
        }
        let container;
        if (isZwnbsp(endContainer)) {
            container = endContainer;
        } else if (
            endOffset === 0 &&
            endContainer.previousSibling?.nodeType === Node.TEXT_NODE &&
            isZwnbsp(endContainer.previousSibling)
        ) {
            // This part of the condition may not be necessary since
            // it seems that endOffset is never set at 0
            container = endContainer.previousSibling;
        }
        if (container) {
            const [anchorNode, anchorOffset] = leftPos(container);
            if (anchorOffset === 0) {
                return;
            }
            const target = childNodes(anchorNode).at(anchorOffset - 1);
            if (target?.matches?.(".oe_thread_beacon")) {
                return target;
            }
        }
    }

    isAllowedBeaconPosition(node) {
        return (
            closestElement(node).nodeName !== "PRE" &&
            (isPhrasingContent(node) ||
                isParagraphRelatedElement(node) ||
                isListItemElement(node) ||
                this.dependencies.baseContainer.isCandidateForBaseContainer(node))
        );
    }

    // TODO ABD: -> CTRL + DELETE needs some custo too (currently deletes too much)
    handleDeleteForward(range) {
        // allow deleteForward to go past a beacon instead of being blocked.
        // TODO ABD: add tests for both cases
        const target = this.identifyNextBeacon(range);
        if (target) {
            const [anchorNode, anchorOffset] = rightPos(target);
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset,
            });
            this.dependencies.delete.delete("forward", "character");
            return true;
        }
    }

    handleDeleteBackward(range) {
        // allow deleteBackward to go past a beacon instead of being blocked.
        const target = this.identifyPreviousBeacon(range);
        if (target) {
            const [anchorNode, anchorOffset] = leftPos(target);
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset,
            });
            this.dependencies.delete.delete("backward", "character");
            return true;
        }
    }

    addCommentToSelection() {
        const { startContainer, startOffset, endContainer, endOffset } =
            this.dependencies.selection.getEditableSelection({ deep: true });
        if (!this.canAddCommentToSelection()) {
            return;
        }
        const previousUndefinedBeacons = [
            ...this.editable.querySelectorAll(".oe_thread_beacon[data-id='undefined']"),
        ];
        this.commentBeaconManager.pendingBeacons = new Set();
        const endBeacon = renderToElement("knowledge.threadBeacon", {
            threadId: "undefined",
            type: "threadBeaconEnd",
            recordId: this.commentsState.articleId,
            recordModel: "knowledge.article",
            peerId: this.peerId,
        });
        this.dependencies.selection.setSelection({
            anchorNode: endContainer,
            anchorOffset: endOffset,
        });
        this.commentBeaconManager.pendingBeacons.add(endBeacon);
        this.dependencies.dom.insert(endBeacon);
        const startBeacon = renderToElement("knowledge.threadBeacon", {
            threadId: "undefined",
            type: "threadBeaconStart",
            recordId: this.commentsState.articleId,
            recordModel: "knowledge.article",
            peerId: this.peerId,
        });
        this.dependencies.selection.setSelection({
            anchorNode: startContainer,
            anchorOffset: startOffset,
        });
        this.commentBeaconManager.pendingBeacons.add(startBeacon);
        this.dependencies.dom.insert(startBeacon);
        this.commentBeaconManager.cleanupThread("undefined");
        for (const beacon of previousUndefinedBeacons) {
            this.removeBeacon(beacon);
        }
        const [anchorNode, anchorOffset] = rightPos(startBeacon);
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
        });
        this.commentsState.displayMode = "handler";
        this.commentsService.createVirtualThread();
        this.commentsState.activeThreadId = "undefined";
        this.dependencies.history.addStep();
    }

    canAddCommentToSelection() {
        const { startContainer, endContainer, isCollapsed } =
            this.dependencies.selection.getEditableSelection({ deep: true });
        return (
            !isCollapsed &&
            this.isAllowedBeaconPosition(startContainer) &&
            this.isAllowedBeaconPosition(endContainer) &&
            isContentEditable(startContainer) &&
            isContentEditable(endContainer)
        );
    }

    onWindowClick(ev) {
        const selector = `.oe-local-overlay, .o_knowledge_comment_box, .o-we-toolbar, .o-overlay-container`;
        const closestElement = ev.target.closest(selector);
        if (!closestElement && !this.editable.contains(ev.target)) {
            this.commentsState.activeThreadId = undefined;
        }
    }

    normalize(elem) {
        this.commentBeaconManager.sortThreads();
        // TODO ABD: think about the fact that a beacon can be normalized in different steps
        // for different users, is this an issue ?
        this.commentBeaconManager.removeBogusBeacons();
        for (const beacon of elem.querySelectorAll(".oe_thread_beacon")) {
            if (beacon.isConnected && !this.isAllowedBeaconPosition(beacon.parentElement)) {
                this.commentBeaconManager.cleanupBeaconPair(beacon.dataset.id);
                this.removeBeacon(beacon);
                continue;
            }
            this.dependencies.linkSelection.padLinkWithZwnbsp(beacon);
            this.dependencies.protectedNode.setProtectingNode(beacon, true);
        }
    }

    cleanZwnbsp(beacon) {
        if (!beacon.isConnected) {
            return;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        if (
            isZwnbsp(beacon.previousSibling) &&
            beacon.previousSibling.previousSibling?.nodeName !== "A"
        ) {
            cursors.update(callbacksForCursorUpdate.remove(beacon.previousSibling));
            beacon.previousSibling.remove();
        }
        if (isZwnbsp(beacon.nextSibling) && beacon.nextSibling.nextSibling?.nodeName !== "A") {
            cursors.update(callbacksForCursorUpdate.remove(beacon.nextSibling));
            beacon.nextSibling.remove();
        }
        cursors.restore();
    }

    removeBeacon(beacon) {
        if (!beacon.isConnected) {
            return;
        }
        this.cleanZwnbsp(beacon);
        const cursors = this.dependencies.selection.preserveSelection();
        const parent = beacon.parentElement;
        cursors.update(callbacksForCursorUpdate.remove(beacon));
        beacon.remove();
        cursors.restore();
        fillEmpty(parent);
        this.dependencies.format.mergeAdjacentInlines(parent);
    }

    updateBeacons() {
        this.commentBeaconManager.sortThreads();
        this.commentBeaconManager.drawThreadOverlays();
    }

    destroy() {
        super.destroy();
        this.alive = false;
        registry.category(this.config.localOverlayContainers.key).remove(this.overlayComponentsKey);
        this.commentBeaconManager.destroy();
        this.localOverlay.remove();
    }

    cleanForSave({ root }) {
        const bogusIds = new Set(["undefined"]);
        for (const beacon of this.commentBeaconManager.bogusBeacons) {
            bogusIds.add(beacon.dataset.id);
        }
        for (const beacon of root.querySelectorAll(".oe_thread_beacon")) {
            if (bogusIds.has(beacon.dataset.id)) {
                beacon.remove();
            } else {
                // remove zwnbsp
                beacon.replaceChildren();
                delete beacon.dataset.peerId;
            }
        }
    }
}
