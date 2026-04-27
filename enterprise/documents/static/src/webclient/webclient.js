import { getDocumentActionRequest } from "@documents/utils";
import { WebClient } from "@web/webclient/webclient";
import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";

patch(WebClient.prototype, {
    /**
     * @override to not open documents in form view.
     */
    loadRouterState() {
        const { resId, model } = router.current.actionStack?.at(-1) || {};
        if (resId && model === "documents.document") {
            return this.actionService.doAction(getDocumentActionRequest(resId));
        }
        return super.loadRouterState(...arguments);
    },
});
