import { registry } from "@web/core/registry";
import { upgradeFrom } from "./upgrade_helpers";
import { getCurrentLocalStorageVersion, LocalStorageEntry } from "@mail/utils/common/local_storage";
import { parseVersion } from "@mail/utils/common/misc";
import { plugin, Plugin } from "@odoo/owl";
import { services } from "@web/core/services";

export class DiscussUpgradePlugin extends Plugin {
    setup() {
        const lse = new LocalStorageEntry("discuss.upgrade.version");
        const oldVersion = lse.get() ?? "1.0";
        const currentVersion = getCurrentLocalStorageVersion();
        lse.set(currentVersion);
        if (parseVersion(oldVersion).isLowerThan(currentVersion)) {
            upgradeFrom(oldVersion);
        }
    }
}

services.add(DiscussUpgradePlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the discuss.upgrade service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("discuss.upgrade", {
    start() {
        return plugin(DiscussUpgradePlugin);
    }
});
