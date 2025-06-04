import { WebsiteSaleFormButton } from "@website_sale/js/form_button";
import { registry } from "@web/core/registry";


export class WebsiteSaleExtraInfoButton extends WebsiteSaleFormButton {
    static selector = "#form_extra_info";
}
registry.category("public.interactions").add("website_sale.extra_info", WebsiteSaleExtraInfoButton);
