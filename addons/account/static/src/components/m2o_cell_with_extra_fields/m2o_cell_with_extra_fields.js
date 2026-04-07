import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One, computeM2OProps } from "@web/views/fields/many2one/many2one";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2OneField, extractM2OFieldProps } from "@web/views/fields/many2one/many2one_field";

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

export class M2OCellWithExtraFields extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2One: Many2OneAccountAccount,
    };
    static template = "account.M2OCellWithExtraFields";
    static props = {
        ...Many2OneField.props,
        parentField: { type: String, optional: true },
    };
    get isReadonlyList() {
        return this.props.record._parentRecord._isReadonly(this.props.parentField);
    }
    get mainM2OProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            // override canOpen to prevent display m2o as link while in draft
            canOpen: !props.readonly || this.isReadonlyList,
        }
    }
}

registry.category("fields").add("m2o_cell_with_extra_fields", {
    component: M2OCellWithExtraFields,
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            parentField: staticInfo.options.parent_field,
        };
    },
});
