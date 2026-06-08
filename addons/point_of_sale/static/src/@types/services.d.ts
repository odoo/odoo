
declare module "services" {
    import { CustomerDisplayDataService } from "@point_of_sale/customer_display/customer_display_data_service";
    import { alertService } from "@point_of_sale/app/services/alert_service";
    import { barcodeReaderService } from "@point_of_sale/app/services/barcode_reader_service";
    import { contextualUtilsService } from "@point_of_sale/app/services/contextual_utils_service";
    import { numberBufferService } from "@point_of_sale/app/services/number_buffer_service";
    import { PosDataService } from "@point_of_sale/app/services/data_service";
    import { PosRouterService } from "@point_of_sale/app/services/pos_router_service";
    import { posTicketPrinterService } from "@point_of_sale/app/services/pos_ticket_printer_service";
    import { posService } from "@point_of_sale/app/services/pos_store";
    import { renderService } from "@point_of_sale/app/services/render_service";
    import { reportService } from "@point_of_sale/app/services/report_service";

    export interface Services {
        alert: typeof alertService;
        barcode_reader: typeof barcodeReaderService;
        contextual_utils_service: typeof contextualUtilsService;
        customer_display_data: typeof CustomerDisplayDataService;
        number_buffer: typeof numberBufferService;
        pos: typeof posService;
        pos_data: typeof PosDataService;
        pos_router: typeof PosRouterService;
        pos_ticket_printer: typeof posTicketPrinterService;
        report: typeof reportService;
    }
}
