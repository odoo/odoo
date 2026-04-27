import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { pick } from "@web/core/utils/objects";

async function studioExportAction(_env, action) {
    await download({
        url: "/web_studio/export",
        data: pick(action.context, ["active_id"]),
    });
}

registry.category("actions").add("studio_export_action", studioExportAction);
