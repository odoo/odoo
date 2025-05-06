// import { renderToElement } from "@web/core/utils/render";
// import { rpc } from "@web/core/network/rpc";
// import { Interaction } from "@web/public/interaction";
// import { registry } from "@web/core/registry";

// export class DynamicEmployeeCard extends Interaction {
//     static selector = ".s_website_dynamic_employee_card";

//     async setup() {
//         try {
//             const employees = await rpc('/get_employee_data', {});
//             if (employees) {
//                 const employeeCardElement = await renderToElement(
//                     'website_dynamic_employee_snippet.dynamic_employee_card',
//                     { employees }
//                 );
//                 this.el.replaceWith(employeeCardElement);
//             }
//         } catch (error) {
//             console.error("Error fetching or rendering employee cards:", error);
//         }
//     }
// }

// registry
//     .category("public.interactions")
//     .add("website_dynamic_employee_snippet.dynamic_employee_card", DynamicEmployeeCard);

import { renderToElement } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.s_website_dynamic_employee_card = publicWidget.Widget.extend({
    selector: ".s_website_dynamic_employee_card",
    disabledInEditableMode: false,

    init() {
        this._super();
        this.orm = this.bindService("orm");
    },

    async willStart() {
        const domain = [["active", "=", true]];

        if (this.el.dataset.department) {
            domain.push([
                "department_id",
                "=",
                parseInt(this.el.dataset.department),
            ]);
        }

        this.employees = await this.orm.searchRead("hr.employee", domain, [
            "id",
            "name",
            "image_1920",
            "job_title",
            "work_email",
            "work_phone",
        ]);
    },

    async start() {
        if (this.employees) {
            const employeeCardElement = await renderToElement(
                "website_dynamic_employee_snippet.dynamic_employee_card",
                { employees: this.employees }
            );
            const replaceableElement = this.el.querySelector(".container");
            replaceableElement?.replaceWith(employeeCardElement);
        }
    },
});
