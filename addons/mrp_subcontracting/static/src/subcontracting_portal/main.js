import { startWebClient } from "@web/start";
import { SubcontractingPortalWebClient } from "./subcontracting_portal";
import { registry } from "@web/core/registry";

const servicesToRemove = ["menu"];

const servicesRegistry = registry.category("services");

/**
 * Remove services unsued in subcontracting portal feature.
 *
 * This function is used before starting the webclient
 * to remove the services that we don't want in the registry.
 * In this case, the home_menu service is removed via the assets
 * but the services in web_studio depends on this service and are not removed.
 * Since this module has not web_studio module in this dependencies, this function will remove
 * the services that we don't want instead of create a new module just to remove the services in assets.
 */
export function removeServices() {
    for (const service of servicesToRemove) {
        if (servicesRegistry.contains(service)) {
            servicesRegistry.remove(service);
        }
    }
}

removeServices();
startWebClient(SubcontractingPortalWebClient);
