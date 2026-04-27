import { setupManager } from "@mail/../tests/helpers/webclient_setup";
import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";

import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(setupManager, {
    setupServiceRegistries() {
        const superHasGroup = user.hasGroup;
        patchUserWithCleanup({
            hasGroup: (group) => group === "base.group_user" || superHasGroup(group),
        });
        return super.setupServiceRegistries(...arguments);
    },
});
