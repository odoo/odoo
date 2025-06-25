import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { Field } from "@web/views/fields/field";

export class HolidaysDaysField extends Field {
    get classNames() {
        const result = super.classNames;
        const { name } = this.props;
        if (name == "holiday_status_id") {
            result.o_readonly_modifier = false;
        }
        return result;
    }
}

export class HolidaysFormController extends FormController {
    static template = "hr_holidays.HolidaysFormView";

    setup() {
        super.setup();
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr_holidays.group_hr_holidays_user");
        });
    }
}

export class HolidaysFormRenderer extends FormRenderer {
    static components = {
        ...FormRenderer.components,
        Field: HolidaysDaysField,
    };
    static props = {
        ...FormRenderer.props,
        isHrUser: { type: Boolean, optional: true },
    };
}

export class HolidaysFormCompiler extends FormCompiler {
    compileField(el, params) {
        const field = super.compileField(el, params);
        const fieldName = el.getAttribute("name");
        // Add all the fields here
        // const readOnlyFields = ["field_1", ..., "field_n"]
        // if (readOnlyFields.includes(fieldName) {}
        if (fieldName == "holiday_status_id") {
            field.setAttribute(
                "readonly",
                `!__comp__.props.isHrUser || __comp__.evaluateBooleanExpr(${JSON.stringify(
                    el.getAttribute("readonly")
                )},__comp__.props.record.evalContextWithVirtualIds) || __comp__.props.readonly`
            );
        }
        return field;
    }
}

export const holidaysFormView = {
    ...formView,
    Compiler: HolidaysFormCompiler,
    Controller: HolidaysFormController,
    Renderer: HolidaysFormRenderer,
};

registry.category("views").add("hr_holidays_form", holidaysFormView);
