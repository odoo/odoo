
declare module "services" {
    import { alertService } from "@point_of_sale/app/services/alert_service";
    import { barcodeReaderService } from "@point_of_sale/app/services/barcode_reader_service";
    import { contextualUtilsService } from "@point_of_sale/app/services/contextual_utils_service";
    import { debugService } from "@point_of_sale/app/services/debug_service";
    import { hardwareProxyService } from "@point_of_sale/app/services/hardware_proxy_service";
    import { numberBufferService } from "@point_of_sale/app/services/number_buffer_service";
    import { PosDataService } from "@point_of_sale/app/services/data_service";
    import { posPrinterService } from "@point_of_sale/app/services/pos_printer_service";
    import { renderService } from "@point_of_sale/app/services/render_service";
    import { reportService } from "@point_of_sale/app/services/report_service";

    export interface Services {
        alert: typeof alertService;
        barcode_reader: typeof barcodeReaderService;
        contextual_utils_service: typeof contextualUtilsService;
        debug: typeof debugService;
        hardware_proxy: typeof hardwareProxyService;
        number_buffer: typeof numberBufferService;
        pos_data: typeof PosDataService;
        printer: typeof posPrinterService;
        renderer: typeof renderService;
        report: typeof reportService;
    }
}
