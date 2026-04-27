import { leftPos, rightPos } from "@html_editor/utils/position";
import { EditorThreadInfo } from "./editor_thread_info";
import { throttleForAnimation } from "@web/core/utils/timing";
import { childNodes } from "@html_editor/utils/dom_traversal";

function binarySearch(comparator, needle, array) {
    let first = 0;
    let last = array.length - 1;
    while (first <= last) {
        const mid = (first + last) >> 1;
        const c = comparator(needle, array[mid]);
        if (c > 0) {
            first = mid + 1;
        } else if (c < 0) {
            last = mid - 1;
        } else {
            return mid;
        }
    }
    return first;
}

export function compareDOMPosition(a, b) {
    const compare = a.compareDocumentPosition(b);
    if (compare & 2) {
        // b before a
        return 1;
    } else if (compare & 4) {
        // a before b
        return -1;
    } else {
        return 0;
    }
}

export function compareBeaconsThreadIds(a, b) {
    const id = (beacon) => parseInt(beacon.dataset.id) || -1;
    const bound = (beacon) => (beacon.dataset.oeType === "threadBeaconStart" ? 0 : 1);
    const idA = id(a);
    const boundA = bound(a);
    const idB = id(b);
    const boundB = bound(b);
    if (idA > idB) {
        return 1;
    } else if (idB > idA) {
        return -1;
    } else if (boundA > boundB) {
        return 1;
    } else if (boundB > boundA) {
        return -1;
    } else {
        return 0;
    }
}

export class CommentBeaconManager {
    constructor({
        commentsState,
        document,
        overlayContainer,
        peerId,
        readonly = false,
        source,
        onStep = () => {},
        removeBeacon = () => {},
        setSelection = () => {},
    } = {}) {
        this.document = document;
        this.source = source;
        this.overlayContainer = overlayContainer;
        this.beacons = [];
        this.searchBeaconIndex = binarySearch.bind(undefined, compareDOMPosition);
        this.beaconsByThreadId = [];
        this.searchBeaconIndexByThreadId = binarySearch.bind(undefined, compareBeaconsThreadIds);
        this.bogusBeacons = new Set();
        this.beaconPairs = {};
        this.sortedThreadIds = [];
        this.cleanups = {};
        this.peerId = peerId;
        this.readonly = readonly;
        this.commentsState = commentsState;
        this.onStep = onStep;
        this.removeBeacon = removeBeacon;
        this.setSelection = setSelection;
        this.drawThreadOverlays = throttleForAnimation(this.drawThreadOverlays.bind(this));
        this.pendingBeacons = new Set();
    }

    addBeacons(beacons) {
        for (const beacon of beacons) {
            const index = this.searchBeaconIndex(beacon, this.beacons);
            this.beacons.splice(index, 0, beacon);
        }
    }

    deleteBeacons(beacons) {
        for (const beacon of beacons) {
            const index = this.searchBeaconIndex(beacon, this.beacons);
            this.beacons.splice(index, 1);
        }
    }

    sortThreads() {
        this.beacons = [...this.source.querySelectorAll(".oe_thread_beacon")];
        this.beaconsByThreadId = this.beacons.toSorted(compareBeaconsThreadIds);
        const starts = {};
        const beaconPairs = {};
        this.bogusBeacons = new Set();
        // loop validates that start is before end for beaconPairs
        for (const beacon of [...this.beacons]) {
            if (beacon.dataset.oeType === "threadBeaconStart") {
                // Don't consider other peers "undefined" beacons
                if (beacon.dataset.id !== "undefined" || beacon.dataset.peerId === this.peerId) {
                    starts[beacon.dataset.id] = {
                        start: beacon,
                    };
                }
                this.bogusBeacons.add(beacon);
            } else if (beacon.dataset.id in starts) {
                const beaconPair = starts[beacon.dataset.id];
                delete starts[beacon.dataset.id];
                beaconPair.end = beacon;
                if (!this.validate(beaconPair)) {
                    this.bogusBeacons.add(beaconPair.end);
                } else {
                    this.preserveExistingBeaconPair(beaconPair);
                    this.removeDuplicate(beaconPair.start);
                    this.removeDuplicate(beaconPair.end);
                    this.bogusBeacons.delete(beaconPair.start);
                    beaconPairs[beacon.dataset.id] = beaconPair;
                }
            } else {
                this.bogusBeacons.add(beacon);
            }
        }
        for (const beacon of [...this.bogusBeacons]) {
            // preserve peer "undefined" beacons
            if (beacon.dataset.id === "undefined" && beacon.dataset.peerId !== this.peerId) {
                this.bogusBeacons.delete(beacon);
            }
        }
        for (const beacon of this.pendingBeacons) {
            // preserve pending beacons
            this.bogusBeacons.delete(beacon);
        }
        const threadIds = new Set(Object.keys(beaconPairs));
        for (const threadId of Object.keys(this.beaconPairs)) {
            if (!threadIds.has(threadId)) {
                this.cleanupThread(threadId);
            }
        }
        const threadIdsToSort = [];
        for (const threadId of threadIds) {
            if (!(threadId in this.beaconPairs)) {
                this.beaconPairs[threadId] = beaconPairs[threadId];
            } else {
                if (this.beaconPairs[threadId].start !== beaconPairs[threadId].start) {
                    this.beaconPairs[threadId].start = beaconPairs[threadId].start;
                }
                if (this.beaconPairs[threadId].end !== beaconPairs[threadId].end) {
                    this.beaconPairs[threadId].end = beaconPairs[threadId].end;
                }
            }
            let editorThread =
                this.commentsState.editorThreads[threadId] ||
                this.commentsState.disabledEditorThreads[threadId];
            if (!editorThread) {
                editorThread = new EditorThreadInfo({
                    beaconPair: this.beaconPairs[threadId],
                    threadId,
                    computeTextMap: this.computeTextMap.bind(this),
                    removeBeaconPair: (beaconPair) => {
                        this.cleanupThread(beaconPair.start.dataset.id);
                        this.removeBeacon(beaconPair.start);
                        this.removeBeacon(beaconPair.end);
                        this.onStep();
                    },
                    setSelectionInBeaconPair: (beaconPair) => {
                        if (this.validate(beaconPair)) {
                            const [anchorNode, anchorOffset] = rightPos(beaconPair.start);
                            this.setSelection({
                                anchorNode,
                                anchorOffset,
                            });
                        }
                    },
                    setBeaconPairId: (beaconPair, id) => {
                        beaconPair.start.dataset.id = id;
                        beaconPair.end.dataset.id = id;
                        this.onStep();
                    },
                    enableBeaconPair: (beaconPair) => {
                        if (this.isDisabled(beaconPair.start)) {
                            this.enable(beaconPair.start);
                        }
                        if (this.isDisabled(beaconPair.end)) {
                            this.enable(beaconPair.end);
                        }
                        const threadId = beaconPair.start.dataset.id;
                        const editorThread = this.commentsState.disabledEditorThreads[threadId];
                        if (editorThread) {
                            this.commentsState.editorThreads[threadId] = editorThread;
                            delete this.commentsState.disabledEditorThreads[threadId];
                        }
                        this.onStep();
                    },
                    disableBeaconPair: (beaconPair) => {
                        if (!this.isDisabled(beaconPair.start)) {
                            this.disable(beaconPair.start);
                        }
                        if (!this.isDisabled(beaconPair.end)) {
                            this.disable(beaconPair.end);
                        }
                        const threadId = beaconPair.start.dataset.id;
                        const editorThread = this.commentsState.editorThreads[threadId];
                        if (editorThread) {
                            this.commentsState.disabledEditorThreads[threadId] = editorThread;
                            delete this.commentsState.editorThreads[threadId];
                        }
                        this.onStep();
                    },
                    isOwned: (beaconPair) => {
                        if (!this.peerId) {
                            return true;
                        } else {
                            const peerId = beaconPair.start.dataset.peerId;
                            return !peerId || this.peerId === peerId;
                        }
                    },
                });
            } else {
                editorThread.beaconPair = this.beaconPairs[threadId];
            }
            if (
                this.isDisabled(this.beaconPairs[threadId].start) ||
                this.isDisabled(this.beaconPairs[threadId].end)
            ) {
                if (!(threadId in this.commentsState.disabledEditorThreads)) {
                    this.commentsState.disabledEditorThreads[threadId] = editorThread;
                }
                if (threadId in this.commentsState.editorThreads) {
                    delete this.commentsState.editorThreads[threadId];
                }
                this.cleanupBeaconPair(threadId);
            } else {
                if (!(threadId in this.commentsState.editorThreads)) {
                    this.commentsState.editorThreads[threadId] = editorThread;
                }
                if (threadId in this.commentsState.disabledEditorThreads) {
                    delete this.commentsState.disabledEditorThreads[threadId];
                }
                threadIdsToSort.push(threadId);
            }
        }
        this.sortedThreadIds = threadIdsToSort.sort((a, b) => {
            return compareDOMPosition(this.beaconPairs[a].start, this.beaconPairs[b].start);
        });
    }

    drawThreadOverlays() {
        const overlayRect = this.overlayContainer.getBoundingClientRect();
        for (const threadId of this.sortedThreadIds) {
            this.cleanupBeaconPair(threadId);
            const beaconPair = this.beaconPairs[threadId];
            if (!beaconPair.start.isConnected || !beaconPair.end.isConnected) {
                continue;
            }
            const range = new Range();
            range.setStart(...rightPos(beaconPair.start));
            range.setEnd(...leftPos(beaconPair.end));
            const clientRects = Array.from(range.getClientRects());
            if (!clientRects.length) {
                continue;
            }
            this.commentsState.editorThreads[threadId].top = clientRects[0].y - overlayRect.y;
            clientRects.reverse();
            const identifyRect = (big, small) => {
                if (big.width === 0 || big.height === 0) {
                    return;
                }
                if (
                    small &&
                    Math.floor(big.x) <= small.x &&
                    Math.floor(big.y) <= small.y &&
                    Math.ceil(big.x + big.width) >= small.x + small.width &&
                    Math.ceil(big.y + big.height) >= small.y + small.height
                ) {
                    return;
                }
                // Faster than elementsFromPoint, but some rects will be omitted
                // if they are under another element like the editor toolbar.
                const target = this.document.elementFromPoint(
                    big.x + big.width / 2,
                    big.y + big.height / 2
                );
                if (!target) {
                    return;
                }
                let valid = true;
                let closestEditable = target.closest("[data-embedded-editable]");
                if (!this.source.contains(closestEditable)) {
                    closestEditable = undefined;
                }
                let embedded = target.closest("[data-embedded]");
                if (!this.source.contains(embedded)) {
                    embedded = undefined;
                }
                if (embedded && (!closestEditable || !embedded.contains(closestEditable))) {
                    valid = false;
                }
                if (!valid || (target.textContent === "" && target.nodeName !== "IMG")) {
                    return;
                }
                return target;
            };
            let previousRect;
            const indicators = [];
            for (const rect of clientRects) {
                const identity = identifyRect(rect, previousRect);
                if (rect.width && rect.height) {
                    previousRect = rect;
                }
                if (!identity || !this.source.contains(identity)) {
                    continue;
                }
                let rectElement;
                let onFocus;
                let onActivate;
                switch (identity.nodeName) {
                    case "IMG":
                        rectElement = this.createImgOverlay(
                            rect,
                            overlayRect,
                            threadId,
                            getComputedStyle(identity)
                        );
                        onFocus = () => {
                            const style = getComputedStyle(identity);
                            rectElement.style.setProperty("border-radius", style.borderRadius);
                            rectElement.style.setProperty(
                                "box-shadow",
                                `0 0 0 8px ${this.getThreadOverlayColor(
                                    this.commentsState.hasFocus(threadId)
                                )}`
                            );
                        };
                        onActivate = onFocus;
                        break;
                    default:
                        rectElement = this.createTextOverlay(rect, overlayRect, threadId);
                        onFocus = () => {
                            rectElement.style.setProperty(
                                "background-color",
                                this.getThreadOverlayColor(this.commentsState.hasFocus(threadId))
                            );
                        };
                        onActivate = onFocus;
                        break;
                }
                if (rectElement) {
                    this.setupOverlayEvents({
                        rectElement,
                        threadId,
                        onFocus,
                        onActivate,
                    });
                    indicators.push(rectElement);
                }
            }
            this.overlayContainer.append(...indicators);
        }
    }

    createTextOverlay(rect, overlayRect, threadId) {
        const { x, y, width, height } = rect;
        const rectElement = this.document.createElement("div");
        rectElement.style = `
            position: absolute;
            top: ${y - overlayRect.y}px;
            left: ${x - overlayRect.x}px;
            width: ${width}px;
            height: ${height}px;
            pointer-events: ${this.readonly ? "auto" : "none"};
            cursor: ${this.readonly ? "grab" : "auto"};
            background-color: ${this.getThreadOverlayColor(this.commentsState.hasFocus(threadId))};
            opacity: 0.5;
        `;
        rectElement.dataset.threadId = threadId;
        return rectElement;
    }

    createImgOverlay(rect, overlayRect, threadId, style) {
        const { x, y, width, height } = rect;
        const rectElement = this.document.createElement("div");
        rectElement.style = `
            position: absolute;
            top: ${y - overlayRect.y}px;
            left: ${x - overlayRect.x}px;
            width: ${width}px;
            height: ${height}px;
            pointer-events: ${this.readonly ? "auto" : "none"};
            cursor: ${this.readonly ? "grab" : "auto"};
            box-shadow: 0 0 0 8px ${this.getThreadOverlayColor(
                this.commentsState.hasFocus(threadId)
            )};
            border-radius: ${style.borderRadius};
            opacity: 0.5;
        `;
        rectElement.dataset.threadId = threadId;
        return rectElement;
    }

    setupOverlayEvents({ rectElement, threadId, onFocus, onActivate }) {
        this.cleanups[threadId] ||= new Set();
        const thread = this.commentsState.editorThreads[threadId];
        if (onActivate) {
            thread.onActivateMap.set(rectElement, onActivate);
        }
        if (onFocus) {
            thread.onFocusMap.set(rectElement, onFocus);
        }
        const onReadonlyActivate = (ev) => {
            thread.onActivate(ev);
        };
        const onReadonlyFocus = (ev) => {
            thread.onFocus(ev);
        };
        if (this.readonly) {
            rectElement.addEventListener("click", onReadonlyActivate);
            rectElement.addEventListener("mouseenter", onReadonlyFocus);
            rectElement.addEventListener("mouseleave", onReadonlyFocus);
        }
        this.cleanups[threadId].add(() => {
            if (this.readonly) {
                rectElement.removeEventListener("click", onReadonlyActivate);
                rectElement.removeEventListener("mouseenter", onReadonlyFocus);
                rectElement.removeEventListener("mouseleave", onReadonlyFocus);
            }
            thread.onActivateMap.delete(rectElement);
            thread.onFocusMap.delete(rectElement);
            rectElement.remove();
        });
    }

    getThreadOverlayColor(focus) {
        return `rgba(27, 161, 228, ${focus ? "0.75" : "0.25"})`;
    }

    computeTextMap(beaconPair) {
        const range = new Range();
        range.setStart(...rightPos(beaconPair.start));
        range.setEnd(...leftPos(beaconPair.end));
        const fragment = range.cloneContents();
        const embeds = [...fragment.querySelectorAll("[data-embedded]")].reverse();
        for (const embed of embeds) {
            embed.replaceWith(...embed.querySelectorAll("[data-embedded-editable]"));
        }
        return childNodes(fragment).map((node) => {
            if (node.nodeName === "IMG") {
                return node.src;
            }
            return node.textContent.trim();
        });
    }

    validate(beaconPair) {
        // is in DOM
        if (!beaconPair.start.isConnected || !beaconPair.end.isConnected) {
            return false;
        }
        // start is before end
        if (compareDOMPosition(beaconPair.start, beaconPair.end) !== -1) {
            return false;
        }
        // is related to the correct article
        if (
            parseInt(beaconPair.start.dataset.res_id) !== this.commentsState.articleId ||
            parseInt(beaconPair.end.dataset.res_id) !== this.commentsState.articleId
        ) {
            return false;
        }
        // is deleted
        if (this.commentsState.deletedThreadIds.has(beaconPair.start.dataset.id)) {
            return false;
        }
        if (
            this.commentsState.activeThreadId !== "undefined" &&
            beaconPair.start.dataset.id === "undefined" &&
            (!this.pendingBeacons.has(beaconPair.start) || !this.pendingBeacons.has(beaconPair.end))
        ) {
            return false;
        }
        // contains no visible text
        if (this.computeTextMap(beaconPair).join("").trim() === "") {
            return false;
        }
        return true;
    }

    removeDuplicate(beacon) {
        // while element at position search compared
        let index = this.searchBeaconIndexByThreadId(beacon, this.beaconsByThreadId);
        let currentBeacon = this.beaconsByThreadId.at(index);
        while (currentBeacon && !compareBeaconsThreadIds(beacon, currentBeacon)) {
            this.beaconsByThreadId.splice(index, 1);
            if (beacon !== currentBeacon) {
                this.bogusBeacons.add(currentBeacon);
                this.deleteBeacons([currentBeacon]);
            }
            index = this.searchBeaconIndexByThreadId(beacon, this.beaconsByThreadId);
            currentBeacon = this.beaconsByThreadId.at(index);
        }
    }

    preserveExistingBeaconPair(beaconPair) {
        // issue: should remove duplicates even if there is no concurrentBeaconPair
        // already exists and is valid elsewhere => keep existing
        const concurrentBeaconPair = this.beaconPairs[beaconPair.start.dataset.id];
        if (
            concurrentBeaconPair &&
            beaconPair !== concurrentBeaconPair &&
            this.validate(concurrentBeaconPair) &&
            compareDOMPosition(concurrentBeaconPair.start, concurrentBeaconPair.end) === -1
        ) {
            if (beaconPair.start !== concurrentBeaconPair.start) {
                beaconPair.start = concurrentBeaconPair.start;
            }
            if (beaconPair.end !== concurrentBeaconPair.end) {
                beaconPair.end = concurrentBeaconPair.end;
            }
        }
    }

    activateRelatedThread(target) {
        this.sortThreads();
        const index = this.searchBeaconIndex(target, this.beacons);
        const ends = {};
        let threadId;
        for (let i = index - 1; i >= 0; i--) {
            const beacon = this.beacons[i];
            if (beacon.dataset.oeType === "threadBeaconEnd") {
                ends[beacon.dataset.id] = {
                    end: beacon,
                };
            } else if (
                beacon.dataset.id in ends ||
                !(beacon.dataset.id in this.beaconPairs) ||
                !this.beaconPairs[beacon.dataset.id].end.isConnected
            ) {
                continue;
            } else if (beacon.dataset.id in this.commentsState.editorThreads) {
                threadId = beacon.dataset.id;
                break;
            }
        }
        this.commentsState.activeThreadId = threadId;
        this.drawThreadOverlays();
    }

    isDisabled(beacon) {
        return beacon.classList.contains("oe_disabled_thread_beacon");
    }

    enable(beacon) {
        beacon.classList.remove("oe_disabled_thread_beacon");
    }

    disable(beacon) {
        beacon.classList.add("oe_disabled_thread_beacon");
    }

    removeBogusBeacons() {
        for (const beacon of this.bogusBeacons) {
            // TODO ABD: evaluate cleanupThread ?
            this.cleanupBeaconPair(beacon.dataset.id);
            this.removeBeacon(beacon);
        }
        this.bogusBeacons = new Set();
    }

    cleanupBeaconPair(threadId) {
        for (const cleanup of this.cleanups[threadId] || []) {
            cleanup();
        }
        delete this.cleanups[threadId];
    }

    destroy() {
        for (const threadId of Object.keys(this.cleanups)) {
            this.cleanupThread(threadId);
        }
        for (const threadId of Object.keys(this.commentsState.editorThreads)) {
            delete this.commentsState.editorThreads[threadId];
        }
        for (const threadId of Object.keys(this.commentsState.disabledEditorThreads)) {
            delete this.commentsState.disabledEditorThreads[threadId];
        }
    }

    cleanupThread(threadId) {
        this.cleanupBeaconPair(threadId);
        delete this.beaconPairs[threadId];
        delete this.commentsState.editorThreads[threadId];
        delete this.commentsState.disabledEditorThreads[threadId];
    }
}
