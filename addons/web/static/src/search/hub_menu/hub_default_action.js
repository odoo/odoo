import { usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { LazySessionPlugin } from "@web/webclient/lazy_session_plugin";
import { getDefaultHubItem, openHubItem } from "./hub_utils";

/**
 * Open the hub of the active record on its default item, resolved client side
 * to spare a server round trip, e.g. <kanban action="hub_default" type="action">.
 */
async function hubDefaultAction(action, options) {
    const actionPlugin = useService("action");
    const lazySession = usePlugin(LazySessionPlugin);
    const { active_model: resModel, active_id: resId } = action.context || {};
    const hubs = await new Promise((resolve) => lazySession.getValue("hubs", resolve));
    const item = resId && getDefaultHubItem(hubs, resModel, resId);
    if (!item) {
        throw new Error(`No hub to open for ${resModel} record ${resId}`);
    }
    return openHubItem(actionPlugin, item, { resModel, resId }, options);
}

registry.category("actions").add("hub_default", hubDefaultAction);
