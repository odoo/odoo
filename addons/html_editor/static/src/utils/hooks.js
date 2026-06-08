import { useExternalListener } from "@web/owl2/utils";

/**
 * Hook to add an external listener to the provided target (document or window),
 * and automatically to the main document/window if they differ (e.g. inside an iframe).
 *
 * @param {Document | Window} target
 * @param {string} eventName
 * @param {function} handler
 * @param {Object} [eventParams]
 */
export function useCrossDocumentListener(target, eventName, handler, eventParams) {
    useExternalListener(target, eventName, handler, eventParams);
    const globalTarget = target.nodeType === Node.DOCUMENT_NODE ? document : window;
    if (target !== globalTarget) {
        useExternalListener(globalTarget, eventName, handler, eventParams);
    }
}
