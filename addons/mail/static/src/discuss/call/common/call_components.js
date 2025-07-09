import { registry } from "@web/core/registry";
import { Call } from "@mail/discuss/call/common/call";

/**
 * Registry used to access components while avoiding cycling dependencies.
 */
const callComponentsRegistry = registry.category("discuss.call/components");

callComponentsRegistry.add("Call", Call);
