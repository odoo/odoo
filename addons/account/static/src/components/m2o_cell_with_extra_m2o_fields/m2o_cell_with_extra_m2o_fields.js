import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One, computeM2OProps } from "@web/views/fields/many2one/many2one";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2OneField, buildM2OFieldDescription } from "@web/views/fields/many2one/many2one_field";

export class Many2XAccountAccountAutocomplete extends Many2XAutocomplete {
    addSearchMoreSuggestion(options) {
        return true;
    }

    async onSearchMore(request) {
        const { getDomain, context, fieldString } = this.props;
        if (request.length) {
            context["search_default_name"] = request;
        }
        const title = _t("Search: %s", fieldString);
        this.selectCreate({
            domain: getDomain(),
            context,
            title,
        });
    }
}

export class Many2OneAccountAccount extends Many2One {
    static components = {
        ...Many2One.components,
        Many2XAutocomplete: Many2XAccountAccountAutocomplete,
    };
}

export class M2OCellWithExtraM2OFields extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2One: Many2OneAccountAccount,
    };
    static template = "account.M2OCellWithExtraM2OFields";
    get mainM2OProps() {
        return computeM2OProps(this.props);
    }
}

registry.category("fields").add("m2o_cell_with_extra_m2o_fields", {
    ...buildM2OFieldDescription(M2OCellWithExtraM2OFields),
    additionalClasses: ["o_field_many2one"],
});
