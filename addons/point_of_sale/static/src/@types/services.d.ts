
declare module "services" {
    import { customerDisplayService } from "@point_of_sale/customer_display/customer_display_service";
    import { alertService } from "@point_of_sale/app/services/alert_service";
    import { barcodeReaderService } from "@point_of_sale/app/services/barcode_reader_service";
    import { posService } from "@point_of_sale/app/services/pos_store";
    import { renderService } from "@point_of_sale/app/services/render_service";
    import { reportService } from "@point_of_sale/app/services/report_service";

    export interface Services {
        alert: typeof alertService;
        barcode_reader: typeof barcodeReaderService;
        customer_display_service: typeof customerDisplayService;
        pos: typeof posService;
        report: typeof reportService;
    }
}
