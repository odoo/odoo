declare module "services" {
    import { reportPrintersCacheService } from "@printer/services/report_printers_cache";

    export interface Services {
        report_printers_cache: typeof reportPrintersCacheService;
    }
}
