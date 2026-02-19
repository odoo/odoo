declare module "services" {
    import { ReportPrintersCacheService } from "@printer/services/report_printers_cache";

    export interface Services {
        report_printers_cache: typeof ReportPrintersCacheService;
    }
}
