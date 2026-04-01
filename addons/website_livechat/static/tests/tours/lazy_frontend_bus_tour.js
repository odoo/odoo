import { WORKER_STATE } from "@bus/services/worker_service";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.lazy_frontend_bus", {
    url: "/",
    steps: () => {
        const busService = odoo.__WOWL_DEBUG__.root.env.services.bus_service;
        if (busService.isActive) {
            throw new Error("The bus service should not be started at page load.");
        }
        patchWithCleanup(busService, {
            start() {
                document.body.classList.add("o-bus-service-started");
                return super.start(...arguments);
            },
        });
        const workerService = odoo.__WOWL_DEBUG__.root.env.services.worker_service;
        if (workerService._state !== WORKER_STATE.UNINITIALIZED) {
            throw new Error("The worker service should not be started at page load.");
        }
        patchWithCleanup(workerService, {
            ensureWorkerStarted() {
                document.body.classList.add("o-worker-service-started");
                return super.ensureWorkerStarted(...arguments);
            },
        });
        odoo.__WOWL_DEBUG__.root.env.services["mail.store"].isReady.then(() =>
            document.body.classList.add("o-mail-store-ready")
        );
        return [
            {
                trigger:
                    "body.o-mail-store-ready:not(.o-bus-service-started):not(.o-worker-service-started)",
            },
            {
                trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
                run: "click",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit Hello, I need help!",
            },
            {
                trigger: "body:not(.o-bus-service-started):not(.o-worker-service-started)",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            { trigger: "body.o-bus-service-started.o-worker-service-started" },
        ];
    },
});
