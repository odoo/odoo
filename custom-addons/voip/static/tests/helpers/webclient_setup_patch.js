/* @odoo-module */

import { setupManager } from "@mail/../tests/helpers/webclient_setup";

import { patch } from "@web/core/utils/patch";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";

patch(setupManager, {
    setupServiceRegistries() {
        const services = registry.category("services");
        services.add("voip.ringtone", {
            start() {
                const ringtones = {
                    dial: {},
                    incoming: {},
                    ringback: {},
                };
                Object.values(ringtones).forEach((r) => Object.assign(r, { play: () => {} }));
                return {
                    ...ringtones,
                    stopPlaying() {},
                };
            },
        });
        if (!services.contains("user")) {
            const fakeUserService = makeFakeUserService((group) => group === "base.group_user");
            services.add("user", fakeUserService);
        }
        return super.setupServiceRegistries(...arguments);
    },
});
