
declare module "services" {
    import { renderService } from "@base_printer/static/src/epson_printer/services/render_service";

    export interface Services {
        renderer: typeof renderService;
    }
}
