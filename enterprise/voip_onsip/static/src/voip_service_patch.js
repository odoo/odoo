import { Voip } from "@voip/core/voip_service";

import { patch } from "@web/core/utils/patch";

patch(Voip.prototype, {
    get areCredentialsSet() {
        return Boolean(this.store.settings.onsip_auth_username) && super.areCredentialsSet;
    },
    get authorizationUsername() {
        return this.store.settings.onsip_auth_username || "";
    },
});
