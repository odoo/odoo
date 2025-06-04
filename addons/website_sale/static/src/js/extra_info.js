import { WebsiteSaleExtraForm } from "@website_sale/js/extra_form";
import { registry } from "@web/core/registry";


export class WebsiteSaleExtraInfoButton extends WebsiteSaleExtraForm {
    static selector = "#form_extra_info";
}
registry.category("public.interactions").add("website_sale.extra_info", WebsiteSaleExtraInfoButton);
