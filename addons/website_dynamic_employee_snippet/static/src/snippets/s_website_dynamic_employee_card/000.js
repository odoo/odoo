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

publicWidget.registry.s_website_dynamic_employee_card =
    publicWidget.Widget.extend({
        selector: ".s_website_dynamic_employee_card",
        disabledInEditableMode: false,
        events: {
            "click .s_website_dynamic_employee_card_load_more_btn": "loadMore",
        },

        init() {
            this._super();
            this.orm = this.bindService("orm");
            this.limit = 6;
        },

        async willStart() {
            this.domain = [["active", "=", true]];

            if (this.el.dataset.department) {
                this.domain.push([
                    "department_id",
                    "=",
                    parseInt(this.el.dataset.department),
                ]);
            }
            this.employeeCount = await this.orm.searchCount("hr.employee", this.domain);
            await this.fetchData();
        },

        async start() {
            await this.renderTemplate();
        },

        async loadMore() {
            this.limit += 6;
            await this.fetchData();
            await this.renderTemplate();
        },

        async renderTemplate() {
            if (this.employees) {

                let employeeCardElement;
                switch (this.el.dataset.view_type) {
                    case "card":
                        employeeCardElement = await renderToElement(
                            "website_dynamic_employee_snippet.dynamic_employee_card",
                            { employees: this.employees }
                        );
                        break;
                    case "list":
                        employeeCardElement = await renderToElement(
                            "website_dynamic_employee_snippet.dynamic_employee_list",
                            { employees: this.employees }
                        );
                        break;
                    default:
                        employeeCardElement = await renderToElement(
                            "website_dynamic_employee_snippet.dynamic_employee_card",
                            { employees: this.employees }
                        );
                }
                const replaceableElement = this.el.querySelector(".container");
                // replaceableElement?.replaceWith(employeeCardElement);
                this.el.replaceChild(employeeCardElement, replaceableElement);

                if (
                    !this.el.querySelector(
                        ".s_website_dynamic_employee_card_load_more_btn"
                    ) && this.limit < this.employeeCount
                ) {
                    const loadMoreBtn = await renderToElement(
                        "website_dynamic_employee_snippet.s_website_dynamic_employee_card_load_more_btn"
                    );
                    this.el.appendChild(loadMoreBtn);
                }
                if (this.limit > this.employeeCount) {
                    this.el.querySelector(".s_website_dynamic_employee_card_load_more_btn")?.remove();
                }
            }
        },

        async fetchData() {
            this.employees = await this.orm.searchRead(
                "hr.employee",
                this.domain,
                [
                    "id",
                    "name",
                    "image_1920",
                    "job_title",
                    "work_email",
                    "work_phone",
                ],
                { limit: this.limit, offset: this.offset }
            );
        },
    });
