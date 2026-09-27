import { registry } from "@web/core/registry";
import { stepUtils } from '@web_tour/tour_utils';
registry.category("web_tour.tours").add('test_mrp_manual_consumption_02', {
    steps: () => [
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last:contains("0.00")',
        },
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last',
            run: 'click',
        },
        {
            trigger: 'div[name="quantity"] input',
            run: "edit 16.0 && click body",
        },
        {
            content: "Click Pager",
            trigger: ".o_pager_value:first()",
            run: "click",
        },
        {
            trigger: "input[id='qty_producing_0']",
            run: "edit 8.0 && click body",
        },
        {
            content: "Click Pager",
            trigger: ".o_pager_value:first()",
            run: "click",
        },
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last:contains("16.00")',
        },
        ...stepUtils.saveForm(),
]});
