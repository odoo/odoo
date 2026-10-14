import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('custom_content_kanban_like_tour', {
    steps: () => [
        {
            trigger: ".o_notebook_headers button[name='pdf_quote_builder']",
            run: "click",
        },
        {
            trigger: "label:contains(Product Document)",
            run: "click",
        },
        {
            trigger: "h5:contains(custom_1) ~ div textarea",
            run: "edit Test && click body",
        },
        ...stepUtils.saveForm(),
    ]
});
