import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Goods Issue Tour
 *
 * Walks the user through the Thai goods issue (ใบเบิกสินค้า) request that
 * extends the OCA stock request workflow with issue type, department,
 * employee and job reference:
 *  1. Open the Stock Requests app
 *  2. Open the Goods Issue list (filtered request list)
 *  3. Create a goods issue request
 *  4. Fill the goods issue information block
 */
registry.category("web_tour.tours").add("od19_goods_issue_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock_request.menu_stock_request_root",
            markup(_t("Let's create a <b>Goods Issue</b> request (ใบเบิกสินค้า)."))
        ),

        {
            trigger: navSection("Operations"),
            content: markup(_t("Open the <b>Operations</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("ใบเบิกสินค้า / Goods Issue"),
            content: markup(_t("Open <b>ใบเบิกสินค้า / Goods Issue</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("ใบเบิกสินค้า / Goods Issue"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "This list only shows the requests flagged as goods issues " +
                "(they carry an issue type)."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to create a goods issue request.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='od19_issue_type_id']",
            content: markup(_t(
                "Choose the <b>issue type</b> (for example material for production or " +
                "office supplies). It is what turns a plain stock request into a goods issue."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='department_id']",
            content: markup(_t("Record the <b>requesting department</b> for cost allocation.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_employee_id']",
            content: markup(_t("Record the <b>employee</b> who takes the goods out.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='od19_reason']",
            content: markup(_t("Explain the <b>reason</b> for the withdrawal.")),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Goods Issue complete! Create a request → set issue type, department and " +
                "employee → add the products to withdraw, then submit it for approval. " +
                "Issue types are maintained in <b>Master Data</b>."
            )),
            run: "click",
        },
    ],
});
