import { printerService } from "@point_of_sale/app/services/printer_service";
import { registry } from "@web/core/registry";
// When their assets are loaded simultaneously during unit tests, it causes a conflict.
// Since we cannot rename services in stable versions, we isolate this here to allow
// removing it from the asset bundle individually for unit testing.
// TODO: Rename the service in the master (saas-18.5) to avoid naming conflicts in the future.
registry.category("services").add("printer", printerService);
