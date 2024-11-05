declare module "services" {
    import { barcodeReaderService } from "@point_of_sale/app/services/barcode_reader_service";
    import { debugService } from "@point_of_sale/app/services/debug_service";
    import { hardwareProxyService } from "@point_of_sale/app/services/hardware_proxy_service";
    import { numberBufferService } from "@point_of_sale/app/services/number_buffer_service";
    import { notificationService } from "@point_of_sale/app/notification/notification_service";
    import { reportService } from "@point_of_sale/app/services/report_service";

    export interface Services {
        barcode_reader: typeof barcodeReaderService;
        debug: typeof debugService;
        hardware_proxy: typeof hardwareProxyService;
        number_buffer: typeof numberBufferService;
        report: typeof reportService;
    }
}
