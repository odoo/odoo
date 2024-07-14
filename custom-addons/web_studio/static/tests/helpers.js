/** @odoo-module */
import { click } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";

import { systrayItem } from "@web_studio/systray_item/systray_item";
import { ormService } from "@web/core/orm_service";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { studioService } from "@web_studio/studio_service";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { resetViewCompilerCache } from "@web/views/view_compiler";
import { fakeColorSchemeService } from "@web/../tests/helpers/mock_services";

export function registerStudioDependencies() {
    const serviceRegistry = registry.category("services");
    registry.category("systray").add("StudioSystrayItem", systrayItem);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);
    serviceRegistry.add("home_menu", homeMenuService);
    serviceRegistry.add("studio", studioService);
    serviceRegistry.add("color_scheme", fakeColorSchemeService);
    registerCleanup(() => resetViewCompilerCache());
}

export async function openStudio(target, params = {}) {
    await click(target.querySelector(".o_main_navbar .o_web_studio_navbar_item button"));
    if (params.noEdit) {
        const studioTabViews = target.querySelector(".o_menu_sections a");
        await click(studioTabViews);
        const controlElm = target.querySelector(
            ".o_action_manager .o_web_studio_editor .o_web_studio_views"
        );
        if (!controlElm) {
            throw new Error("We should be in the Tab 'Views' but we are not");
        }
    }
    if (params.report) {
        const studioTabReport = target.querySelectorAll(".o_menu_sections a")[1];
        await click(studioTabReport);
        let controlElm = target.querySelector(
            ".o_action_manager .o_web_studio_editor .o_studio_report_kanban_view"
        );
        if (!controlElm) {
            throw new Error("We should be in the Tab 'Report' but we are not");
        }
        await click(controlElm.querySelector(`.o_kanban_record [data-id="${params.report}"`));
        controlElm = target.querySelector(
            ".o_action_manager .o_web_studio_editor .o_web_studio_report_editor_manager"
        );
        if (!controlElm) {
            throw new Error("We should be editing the first report that showed up");
        }
    }
}

export function leaveStudio(target) {
    return click(target.querySelector(".o_studio_navbar .o_web_studio_leave a"));
}

export function getReportServerData() {
    const models = {
        "ir.actions.report": {
            fields: {
                model: { type: "char" },
                report_name: { type: "char" },
                report_type: { type: "char" },
            },
            records: [{ id: 11, model: "foo", report_name: "foo_report", report_type: "pdf" }],
        },
    };

    const views = {
        "ir.actions.report,false,kanban": `
            <kanban js_class="studio_report_kanban">
                <field name="report_name"/>
                <field name="report_type"/>
                <field name="id"/>
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click" t-att-data-id="record.id.value">
                            <div class="oe_kanban_details">
                                <field name="report_name" groups="base.group_no_one"/>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        "ir.actions.report,false,search": `<search />`,
    };

    return { models, views };
}

export function fillActionFieldsDefaults(action) {
    if (action.type !== "ir.actions.act_window") {
        return action;
    }
    action = { ...action };
    if (!("groups_id" in action)) {
        action.groups_id = [];
    }
    if (!("view_mode" in action)) {
        action.view_mode = action.views.map((v) => v[0]).join(",");
    }
    if (!("name" in action)) {
        action.name = "";
    }
    if (!("help" in action)) {
        action.help = "";
    }
    return action;
}
