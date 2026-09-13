// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";

const log = makeLogger("web.ui.popover.target");

/** @type {Map<Node, { observer: MutationObserver, watchers: Map<Node, Set<() => void>> }>} */
const watchersByRoot = new Map();

/** @param {Node} root */
function checkRoot(root) {
    const entry = watchersByRoot.get(root);
    if (!entry) {
        return;
    }
    /** @type {Node[] | undefined} */
    let changedTargets;
    for (const target of entry.watchers.keys()) {
        if (!target.isConnected || target.getRootNode() !== root) {
            (changedTargets ??= []).push(target);
        }
    }
    if (!changedTargets) {
        return;
    }
    for (const target of changedTargets) {
        const callbacks = entry.watchers.get(target);
        if (!callbacks) {
            continue;
        }
        for (const callback of [...callbacks]) {
            callback();
        }
    }
}

/**
 * @param {Node} root
 * @param {Node} target
 * @param {() => void} onChanged
 * @returns {() => void}
 */
function watchRoot(root, target, onChanged) {
    let entry = watchersByRoot.get(root);
    if (!entry) {
        const observer = new MutationObserver(() => checkRoot(root));
        observer.observe(root, { childList: true, subtree: true });
        entry = { observer, watchers: new Map() };
        watchersByRoot.set(root, entry);
    }
    let callbacks = entry.watchers.get(target);
    if (!callbacks) {
        callbacks = new Set();
        entry.watchers.set(target, callbacks);
    }
    callbacks.add(onChanged);

    return () => {
        const current = watchersByRoot.get(root);
        const targetCallbacks = current?.watchers.get(target);
        if (!current || !targetCallbacks) {
            return;
        }
        targetCallbacks.delete(onChanged);
        if (!targetCallbacks.size) {
            current.watchers.delete(target);
        }
        if (!current.watchers.size) {
            current.observer.disconnect();
            watchersByRoot.delete(root);
        }
    };
}

/**
 * @param {Node} target
 * @param {() => void} onDetached
 * @returns {() => void}
 */
export function watchForDetachedTarget(target, onDetached) {
    /** @type {Node} */
    let root;
    let disposed = false;
    let disposeRoot = () => {};
    let disposeHost = () => {};

    function checkTarget() {
        if (disposed) {
            return;
        }
        if (!target.isConnected) {
            log.lifecycle("detached");
            onDetached();
        } else if (target.getRootNode() !== root) {
            subscribe();
        }
    }

    function subscribe() {
        disposeRoot();
        disposeHost();
        root = target.isConnected
            ? target.getRootNode()
            : (target.ownerDocument ?? document);
        disposeRoot = watchRoot(root, target, checkTarget);
        // A host is removed in its parent's tree, not inside its shadow root.
        const host = /** @type {ShadowRoot} */ (root).host;
        disposeHost = host ? watchForDetachedTarget(host, checkTarget) : () => {};
        log.lifecycle("watch", { shadow: Boolean(host), roots: watchersByRoot.size });
    }

    subscribe();
    return () => {
        disposed = true;
        disposeRoot();
        disposeHost();
        log.lifecycle("unwatch", { roots: watchersByRoot.size });
    };
}

/** @returns {number} */
export function getDetachedTargetObserverCount() {
    return watchersByRoot.size;
}
