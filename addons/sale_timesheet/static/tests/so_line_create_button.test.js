import { describe, expect, test } from "@odoo/hoot";
import { click, edit, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { focus, mailModels } from "@mail/../tests/mail_test_helpers";
import { contains, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineSaleTimesheetModels, saleTimesheetModels } from "./sale_timesheet_test_helpers";

describe.current.tags("desktop");

class SaleOrder extends saleTimesheetModels.SaleOrder {
    _views = {
        form: `
            <form>
                <group>
                    <field name="partner_id" required="True"/>
                    <field name="project_id"/>
                </group>
                <notebook>
                    <page string="Order Lines" name="order_lines">
                        <field name="order_line">
                            <list editable="bottom">
                                <field name="product_id"/>
                            </list>
                        </field>
                    </page>
                </notebook>
            </form>
        `,
    };
}

class ProjectProject extends saleTimesheetModels.ProjectProject {
    _views = {
        form: `
            <form>
                <notebook>
                    <page name="billing_employee_rate" string="Invoicing">
                        <field name="sale_line_employee_ids">
                            <list editable="bottom">
                                <field name="employee_id" widget="many2one_avatar_user"/>
                                <field name="sale_line_id" required="True"
                                    options="{'no_create': True, 'no_open': True}"
                                    context="{
                                        'default_partner_id': 1,
                                        'default_project_id': 1,
                                    }"
                                    widget="so_line_create_button"
                                />
                                <field name="price_unit"/>
                            </list>
                        </field>
                    </page>
                </notebook>
            </form>
        `,
    };
}

saleTimesheetModels.ProjectProject = ProjectProject;
saleTimesheetModels.SaleOrder = SaleOrder;

defineSaleTimesheetModels();

onRpc("get_first_service_line", function ({ args, model }) {
    const [solId] = this.env[model].browse(args[0])[0].order_line;
    const productId = this.env["sale.order.line"].browse(solId)[0].product_id;
    const productType = this.env["product.product"].browse(productId)[0].type;
    if (productType === "service") {
        expect.step("valid_so");
        return [solId];
    } else {
        expect.step("invalid_so");
        return false;
    }
});

test("test so_line_create_button widget: valid SO", async () => {
    const partner_name = mailModels.ResPartner._records.find((partner) => partner.id === 1).name;
    const project_name = ProjectProject._records.find((project) => project.id === 1).name;
    await mountView({
        resId: 1,
        resModel: "project.project",
        type: "form",
    });

    await contains(".o_field_x2many_list_row_add button").click();
    await focus("[name='sale_line_id'] input");
    const create_so_button = queryOne("a[aria-label='Create Sales Order']");
    expect(create_so_button).toBeVisible({
        message: "The so_line_create_button widget should appear when creating a new record.",
    });
    await create_so_button.click();
    await animationFrame();

    expect("div[name='partner_id'] input").toHaveValue(partner_name, {
        message:
            "The default_partner_id set in the field context should be passed in the SO form view.",
    });
    expect("div[name='project_id'] input").toHaveValue(project_name, {
        message:
            "The default_project_id set in the field context should be passed in the SO form view.",
    });

    await contains(".modal-content .o_field_x2many_list_row_add button").click();
    await contains(".modal-content .o_selected_row td[name='product_id'] input").edit(
        "Service Product 2"
    );
    await contains(".modal-content .ui-sortable .o-autocomplete--input").click();
    await contains(".dropdown-item:nth-child(1)").click();
    await contains(".modal-content button[class*='o_form_button_save']").click();

    expect(".o_selected_row td[name='sale_line_id'] input").toHaveValue("Service Product 2", {
        message: "The sale order line should be created and set in the input field.",
    });
    // As the SO contains at least one service product, it should be validated and created.
    expect.verifySteps(["valid_so"]);
});

test("test so_line_create_button widget: invalid SO", async () => {
    await mountView({
        resId: 1,
        resModel: "project.project",
        type: "form",
    });

    await contains(".o_field_x2many_list_row_add button").click();
    await focus("[name='sale_line_id'] input");
    await contains("a[aria-label='Create Sales Order']").click();
    await animationFrame();

    await contains(".modal-content .o_field_x2many_list_row_add button").click();
    await contains(".modal-content .o_selected_row td[name='product_id'] input").edit(
        "Consumable Product 1"
    );
    await contains(".modal-content .ui-sortable .o-autocomplete--input").click();
    await contains(".dropdown-item:nth-child(1)").click();
    await contains(".modal-content button[class*='o_form_button_save']").click();

    expect(".o_selected_row td[name='sale_line_id'] input").toHaveValue("", {
        message: "The sale order line should not be created and set in the input field.",
    });
    // As the SO does not contain at least one service product, it should not be validated and created.
    expect.verifySteps(["invalid_so"]);
});

test("test so_line_create_button widget: visibility conditions", async () => {
    await mountView({
        resId: 1,
        resModel: "project.project",
        type: "form",
    });

    await click(".ui-sortable .o_data_row:nth-child(1) div[name='sale_line_id']");
    await animationFrame();
    await focus("[name='sale_line_id'] input");
    expect("a[aria-label='Create Sales Order']").toHaveCount(0, {
        message:
            "The so_line_create_button widget should not appear as there is already a value in sale_line_id field.",
    });
    await edit("");
    await click(".ui-sortable .o_data_row:nth-child(1) div[name='employee_id']");
    await animationFrame();
    await focus("[name='sale_line_id'] input");
    expect("a[aria-label='Create Sales Order']").toBeVisible({
        message:
            "The so_line_create_button widget should appear as there is no value in sale_line_id field.",
    });
});
