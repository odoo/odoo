import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2One } from "@web/views/fields/many2one/many2one";
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

export class Many2OneFieldAccountAccount extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2One: Many2OneAccountAccount,
    };
}

registry.category("fields").add("many2one_account_account", {
    ...buildM2OFieldDescription(Many2OneFieldAccountAccount),
    additionalClasses: ["o_field_many2one"],
});
