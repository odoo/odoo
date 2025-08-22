import { registry } from "@web/core/registry";
import { Call } from "@mail/discuss/call/common/call";
import { Meeting } from "@mail/discuss/call/common/meeting";

/**
 * Registry used to access components while avoiding cycling dependencies.
 */
const callComponentsRegistry = registry.category("discuss.call/components");

callComponentsRegistry.add("Call", Call).add("Meeting", Meeting);
