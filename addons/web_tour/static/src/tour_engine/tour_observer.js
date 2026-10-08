const MUTATION_OPTIONS = {
    attributes: true,
    childList: true,
    subtree: true,
    characterData: true,
};

/**
 * Calls `onChange` whenever the DOM may have changed: on any mutation of the
 * observed document, of its iframes (including after they reload) and of its
 * shadow roots, and periodically every {@link TourObserver.CHECK_INTERVAL}
 * ms as a fallback for changes that don't mutate the DOM.
 */
export class TourObserver {
    static CHECK_INTERVAL = 2000;

    /**
     * @param {() => void} onChange
     */
    constructor(onChange) {
        this.onChange = onChange;
        this.observedIframes = new WeakSet();
        this.listenersController = new AbortController();
        this.observer = new MutationObserver((records) => {
            onChange();
            for (const record of records) {
                for (const node of record.addedNodes) {
                    this.observeInside(node);
                }
            }
        });
    }

    /**
     * @param {Document} doc
     */
    start(doc) {
        this.observeRoot(doc);
        this.interval = setInterval(this.onChange, TourObserver.CHECK_INTERVAL);
    }

    disconnect() {
        this.observer.disconnect();
        clearInterval(this.interval);
        this.listenersController.abort();
    }

    /**
     * @param {Document | ShadowRoot} root
     */
    observeRoot(root) {
        this.observer.observe(root, MUTATION_OPTIONS);
        this.observeInside(root);
    }

    /**
     * @param {Node} node
     */
    observeInside(node) {
        if (
            ![Node.ELEMENT_NODE, Node.DOCUMENT_NODE, Node.DOCUMENT_FRAGMENT_NODE].includes(
                node.nodeType
            )
        ) {
            return;
        }
        if (node.nodeName === "IFRAME") {
            this.observeIframe(node);
        }
        for (const iframe of node.querySelectorAll("iframe")) {
            this.observeIframe(iframe);
        }
        if (node.shadowRoot) {
            this.observeRoot(node.shadowRoot);
        }
        for (const el of node.querySelectorAll("*")) {
            if (el.shadowRoot) {
                this.observeRoot(el.shadowRoot);
            }
        }
    }

    /**
     * @param {HTMLIFrameElement} iframe
     */
    observeIframe(iframe) {
        if (this.observedIframes.has(iframe)) {
            return;
        }
        this.observedIframes.add(iframe);
        const observeContent = () => {
            if (iframe.contentDocument) {
                this.onChange();
                this.observeRoot(iframe.contentDocument);
            }
        };
        observeContent();
        iframe.addEventListener("load", observeContent, {
            signal: this.listenersController.signal,
        });
    }
}
