import { browser } from "@web/core/browser/browser";
import { isIosApp } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { mainTabLocalStorageService } from "@bus/main_tab_local_storage_service";
import { electionWorkerService } from "@bus/main_tab_election_worker_service";

export const mainTabService =
    browser.SharedWorker && !isIosApp() ? electionWorkerService : mainTabLocalStorageService;

registry.category("services").add("main_tab", mainTabService);
