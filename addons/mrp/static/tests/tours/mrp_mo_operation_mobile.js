import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("test_mo_operation_kept_on_mobile", {
    steps: () => [
        {
            trigger: '.o_field_widget[name="product_id"] input',
            run: "click",
        },
        {
            trigger: '.modal .o_kanban_record:contains("test1")',
            run: "click",
        },
        ...stepUtils.saveForm(),
    ],
});
