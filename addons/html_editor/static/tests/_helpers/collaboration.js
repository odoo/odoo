import { HistoryPlugin } from "@html_editor/core/history_plugin";
import { CollaborationPlugin } from "@html_editor/others/collaboration/collaboration_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { createDOMPathGenerator } from "@html_editor/utils/dom_traversal";
import { DIRECTIONS } from "@html_editor/utils/position";
import { after, expect } from "@odoo/hoot";
import { setupEditor } from "./editor";

/**
 *
 * @typedef { import("@html_editor/editor").Editor } Editor
 *
 * @typedef { Object } PeerInfo
 * @property { string } peerId
 * @property { import("@html_editor/core/history_plugin").HistoryStep[] } steps
 * @property { Editor } editor
 * @property { import("@html_editor/collaboration/collaboration_plugin").CollaborationPlugin } collaborationPlugin
 * @property { import("@html_editor/plugin").HistoryPlugin } historyPlugin
 *
 * @typedef { Object } MultiEditorSpec
 * @property { string[] } peerIds
 * @property { string } contentBefore
 * @property { string } contentAfter
 * @property { Plugin[] } Plugins
 * @property { (peerInfos: Record<string, PeerInfo>) => Promise<void> } afterCreate
 * @property { (peerInfos: Record<string, PeerInfo>) => Promise<void> } afterCursorInserted
 *
 * @typedef { Object } EditorSelection
 * @property { Node } anchorNode
 * @property { number } anchorOffset
 * @property { Node } focusNode
 * @property { number } focusOffset
 */

function historyMissingParentSteps(peerInfos, peerInfo, { step, fromStepId }) {
    const missingSteps = peerInfos[step.peerId].collaborationPlugin.historyGetMissingSteps({
        fromStepId,
        toStepId: step.id,
    });
    if (missingSteps === -1 || !missingSteps.length) {
        throw new Error("Impossible to get the missing steps.");
    }
    peerInfo.collaborationPlugin.onExternalHistorySteps(missingSteps.concat([step]));
}

/**
 * Setup a editor with multiple peers
 *
 * @param { MultiEditorSpec } spec
 * @returns { Promise<void> }
 */
export const setupMultiEditor = async (spec) => {
    /** @type { Record<string, PeerInfo> } */
    const peerInfos = {};
    const peerIds = spec.peerIds;
    const initialHystoryPluginGenerateId = HistoryPlugin.prototype.generateId;
    after(() => {
        HistoryPlugin.prototype.generateId = initialHystoryPluginGenerateId;
    });

    for (const peerId of peerIds) {
        const peerInfo = {
            peerId,
            steps: [],
        };
        peerInfos[peerId] = peerInfo;
        let n = 0;
        HistoryPlugin.prototype.generateId = () => `fake_id_${n++}`;
        let selection;
        const defaultPlugins = MAIN_PLUGINS;
        const base = await setupEditor(spec.contentBefore, {
            props: { iframe: true },
            onMounted: (editable) => {
                selection = parseMultipleTextualSelection(editable, peerId);
            },
            config: {
                Plugins: [...defaultPlugins, CollaborationPlugin, ...(spec.Plugins || [])],
                collaboration: { peerId },
                resources: {
                    ...spec.resources,
                    collaboration_step_added_handlers: (step) => {
                        peerInfo.steps.push(step);
                    },
                    history_missing_parent_step_handlers: (params) => {
                        historyMissingParentSteps(peerInfos, peerInfo, params);
                    },
                },
            },
        });
        peerInfo.editor = base.editor;
        if (selection && selection.anchorNode) {
            base.editor.shared.selection.setSelection(selection);
            base.plugins.get("history").stageSelection();
        } else {
            base.editor.document.getSelection().removeAllRanges();
        }
        peerInfo.plugins = base.plugins;
        // TODO @phoenix refactor tests, no need to assign every plugin individually
        const getPlugin = (id) => base.editor.plugins.find((x) => x.constructor.id === id);
        peerInfo.collaborationPlugin = getPlugin("collaboration");
        peerInfo.historyPlugin = getPlugin("history");
    }

    const peerInfosList = Object.values(peerInfos);

    // Init the editors

    // From now, any any step from a peer must have a different ID.
    let concurrentNextId = 1;
    for (const { historyPlugin } of peerInfosList) {
        historyPlugin.generateId = () => "fake_concurrent_id_" + concurrentNextId++;
        historyPlugin.currentStep.id = historyPlugin.generateId();
    }

    after(() => {
        for (const peerInfo of peerInfosList) {
            peerInfo.editor.destroy();
        }
    });
    return peerInfos;
};

export async function testMultiEditor(spec) {
    const peerInfos = await setupMultiEditor(spec);

    if (spec.afterCreate) {
        await spec.afterCreate(peerInfos);
    }

    renderTextualSelection(peerInfos);

    if (spec.contentAfter) {
        validateContent(peerInfos, spec.contentAfter);
    }
    if (spec.afterCursorInserted) {
        await spec.afterCursorInserted(peerInfos);
    }
    return peerInfos;
}

export const applyConcurrentActions = (peerInfos, concurrentActions) => {
    const peerInfosList = Object.values(peerInfos);
    for (const peerInfo of peerInfosList) {
        if (typeof concurrentActions[peerInfo.peerId] === "function") {
            concurrentActions[peerInfo.peerId](peerInfo.editor);
        }
    }
};

export const mergePeersSteps = (peerInfos) => {
    const peerInfosList = Object.values(peerInfos);
    for (const peerInfoA of peerInfosList) {
        for (const peerInfoB of peerInfosList) {
            if (peerInfoA === peerInfoB) {
                continue;
            }
            for (const step of peerInfoB.steps) {
                peerInfoA.collaborationPlugin.onExternalHistorySteps([
                    JSON.parse(JSON.stringify(step)),
                ]);
            }
        }
    }
};

/**
 * @param {Record<string, PeerInfo>} peerInfos
 */
export const validateSameHistory = (peerInfos) => {
    const peerInfosList = Object.values(peerInfos);

    const PeerInfo = peerInfosList[0];
    const historyLength = PeerInfo.historyPlugin.steps.length;

    for (const peerInfo of peerInfosList.slice(1)) {
        expect(peerInfo.historyPlugin.steps.length).toBe(historyLength, {
            message: "The history size should be the same.",
        });
        for (let i = 0; i < historyLength; i++) {
            expect(PeerInfo.historyPlugin.steps[i].id).toBe(peerInfo.historyPlugin.steps[i].id, {
                message: `History steps are not consistent accross peers.`,
            });
        }
    }
};

export const validateContent = (peerInfos, content) => {
    for (const peerInfo of Object.values(peerInfos)) {
        const value = peerInfo.editor.editable.innerHTML;
        expect(value).toBe(content, {
            message: `error with peer ${peerInfo.peerId}`,
        });
    }
};

/**
 * @param {Record<string, PeerInfo>} peerInfos
 */
export function renderTextualSelection(peerInfos) {
    const peerInfosList = Object.values(peerInfos);
    const cursorNodes = {};
    for (const peerInfo of peerInfosList) {
        const iframeDocument = peerInfo.editor.document;
        const historyPlugin = peerInfo.historyPlugin;
        const peerSelection = iframeDocument.getSelection();
        if (peerSelection.anchorNode === null) {
            continue;
        }

        const { anchorNode, anchorOffset, focusNode, focusOffset } = peerSelection;

        const peerId = peerInfo.peerId;
        const focusNodeId = historyPlugin.nodeMap.getId(focusNode);
        const anchorNodeId = historyPlugin.nodeMap.getId(anchorNode);
        cursorNodes[focusNodeId] = cursorNodes[focusNodeId] || [];
        cursorNodes[focusNodeId].push({ type: "focus", peerId, offset: focusOffset });
        cursorNodes[anchorNodeId] = cursorNodes[anchorNodeId] || [];
        cursorNodes[anchorNodeId].push({ type: "anchor", peerId, offset: anchorOffset });
    }

    for (const nodeId of Object.keys(cursorNodes)) {
        cursorNodes[nodeId] = cursorNodes[nodeId].sort(
            (a, b) => b.offset - a.offset || b.peerId.localeCompare(a.peerId)
        );
    }

    for (const peerInfo of peerInfosList) {
        const historyPlugin = peerInfo.historyPlugin;
        for (const [nodeId, cursorsData] of Object.entries(cursorNodes)) {
            const node = historyPlugin.nodeMap.getNode(nodeId);
            for (const cursorData of cursorsData) {
                const cursorString =
                    cursorData.type === "anchor"
                        ? `[${cursorData.peerId}}`
                        : `{${cursorData.peerId}]`;
                insertCharsAt(cursorString, node, cursorData.offset);
            }
        }
    }
}

/**
 * Inserts the given characters at the given offset of the given node.
 *
 * @param {string} chars
 * @param {Node} node
 * @param {number} offset
 */
export function insertCharsAt(chars, node, offset) {
    const document = node.ownerDocument;
    if (node.nodeType === Node.TEXT_NODE) {
        const startValue = node.nodeValue;
        if (offset < 0 || offset > startValue.length) {
            throw new Error(`Invalid ${chars} insertion in text node`);
        }
        node.nodeValue = startValue.slice(0, offset) + chars + startValue.slice(offset);
    } else {
        if (offset < 0 || offset > node.childNodes.length) {
            throw new Error(`Invalid ${chars} insertion in non-text node`);
        }
        const textNode = document.createTextNode(chars);
        if (offset < node.childNodes.length) {
            node.insertBefore(textNode, node.childNodes[offset]);
        } else {
            node.appendChild(textNode);
        }
    }
}

const inScopeTraversal = createDOMPathGenerator(DIRECTIONS.RIGHT, { inScope: true });

/**
 * @param {Node} rootElement
 * @returns {Record<string, EditorSelection>}
 */
function parseMultipleTextualSelection(rootElement, peerId) {
    /** @type { EditorSelection } */
    const selection = {
        anchorNode: null,
        anchorOffset: null,
        focusNode: null,
        focusOffset: null,
    };
    for (const currentNode of [rootElement, ...inScopeTraversal(rootElement, 0)]) {
        if (currentNode.nodeType === Node.TEXT_NODE) {
            // Look for special characters in the text content and remove them.
            let match;
            const regex = new RegExp(/(?:\[(\w+)\})|(?:\{(\w+)])/, "gd");
            while ((match = regex.exec(currentNode.textContent))) {
                regex.lastIndex = 0;
                const indexes = match.indices[0];

                if (match[0].includes("}")) {
                    const selectionPeerId = match[1];
                    if (selectionPeerId === peerId) {
                        selection.anchorNode = currentNode;
                        selection.anchorOffset = indexes[0];
                    }
                } else {
                    const selectionPeerId = match[2];
                    if (selectionPeerId === peerId) {
                        selection.focusNode = currentNode;
                        selection.focusOffset = indexes[0];
                    }
                }
                currentNode.textContent =
                    currentNode.textContent.slice(0, indexes[0]) +
                    currentNode.textContent.slice(indexes[1]);
            }
        }
    }

    return selection;
}
