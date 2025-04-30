import { registry } from "@web/core/registry";

registry.category("mock_rpc").add("/bus/has_missed_notifications", () => false);
