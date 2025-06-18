import { registry } from "@web/core/registry";

const mockRegistry = registry.category("mock_rpc");

mockRegistry.add("get_installed", ({ model }) => {
    if (model === "res.lang") {
        return [["en_US", "English (US)"]];
    }
});
