import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { multiTabFallbackService } from "@bus/multi_tab_fallback_service";
import { multiTabSharedWorkerService } from "@bus/multi_tab_shared_worker_service";

export const multiTabService = browser.SharedWorker
    ? multiTabSharedWorkerService
    : multiTabFallbackService;

registry.category("services").add("multi_tab", multiTabService);
