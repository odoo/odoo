import { registry } from "@web/core/registry";
import { computeM2OProps } from "@web/views/fields/many2one/many2one";
import { Many2OneField, extractM2OFieldProps } from "@web/views/fields/many2one/many2one_field";

export class M2OCellWithExtraM2OFields extends Many2OneField {
    static template = "account.M2OCellWithExtraM2OFields";
    get mainM2OProps() {
        return computeM2OProps(this.props);
    }
}

registry.category("fields").add("m2o_cell_with_extra_m2o_fields", {
    component: M2OCellWithExtraM2OFields,
    extractProps: extractM2OFieldProps,
});
