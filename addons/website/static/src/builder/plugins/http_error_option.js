import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";

const HTTP_ERROR_PAGES = {
    "http_routing.4xx": "website.4xx_hide_error",
    "http_routing.400": "website.400_hide_error",
    "http_routing.403": "website.403_hide_error",
    "http_routing.415": "website.415_hide_error",
    "http_routing.422": "website.422_hide_error",
};

export class HttpErrorOption extends BaseOptionComponent {
    static id = "http_error_option";
    static template = "website.httpErrorOption"

    setup() {
        super.setup();
        const currentPage = this.document.documentElement.dataset.viewXmlid;
        this.templatePage = HTTP_ERROR_PAGES[currentPage] ? [HTTP_ERROR_PAGES[currentPage]] : [];
    }
}

registry.category("website-options").add(HttpErrorOption.id, HttpErrorOption);
