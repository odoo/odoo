import * as viewHelpers from "@web/../tests/views/helpers";
import * as webClientHelpers from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

function registerFakemailPopoutService() {
    if (!serviceRegistry.contains("mail.popout")) {
        serviceRegistry.add("mail.popout", {
            start() {
                return {
                    get externalWindow() {
                        return null;
                    },
                    popout() {},
                    reset() {},
                };
            },
        });
    }
}

const superSetupViewRegistries = viewHelpers.setupViewRegistries
viewHelpers.setupViewRegistries = () => {
    registerFakemailPopoutService()
    return superSetupViewRegistries();
}

const superSetupWebClientRegistries = webClientHelpers.setupWebClientRegistries
webClientHelpers.setupWebClientRegistries = () => {
    registerFakemailPopoutService()
    return superSetupWebClientRegistries();
}

const superCreateWebClient = webClientHelpers.createWebClient
webClientHelpers.createWebClient = (params) => {
    registerFakemailPopoutService()
    return superCreateWebClient(params);
}
