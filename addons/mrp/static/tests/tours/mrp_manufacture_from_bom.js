import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_manufacture_from_bom", {
    steps: () => [
        {
            trigger: '[name="product_tmpl_id"]',
            run: "click",
        },
        {
            trigger: '.o_stat_text:contains("BoM Overview")',
            run: "click",
        },
        {
            trigger: '.fa-toggle-off',
            run: "click",
        },
        {
            trigger: 'button.btn-primary:contains("Manufacture")',
            run: "click",
        },
        {
            trigger: 'button[aria-checked="true"]:contains("Draft")',
        },
    ],
});
