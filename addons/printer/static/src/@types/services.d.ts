declare module "services" {
    import { ReportPrintersCachePlugin } from "@printer/services/report_printers_cache_plugin";

    export interface Services {
        report_printers_cache: ReportPrintersCachePlugin;
    }
}
