import { registry } from "@web/core/registry";

const mockRegistry = registry.category("mock_rpc");

mockRegistry.add("/web/dataset/call_kw/res.lang/get_installed", async function (request) {
    return [["en_US", "English (US)"]];
});
