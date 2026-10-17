import { Component, proxy, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const RELATIONAL_TYPES = ["many2one", "many2many", "one2many"];

/**
 * Autocomplete listing first the records the offending value matched.
 */
export class ImportMatchAutocomplete extends Many2XAutocomplete {
    get sources() {
        return [...this.props.otherSources, this.optionsSource];
    }
    addStartTypingSuggestion() {
        return false;
    }
}

export class ImportErrorResolution extends Component {
    static template = "ImportErrorResolution";
    static components = { ImportMatchAutocomplete, SelectMenu };

    props = useProps({
        error: t.object(),
        fieldInfo: t.object(),
        onResolve: t.function(),
    });

    setup() {
        this.orm = useService("orm");
        this.state = proxy({ isPicking: false });
    }

    get resolution() {
        return this.props.error.resolution || {};
    }

    /**
     * A column mapped on the external or database id of a relation (e.g.
     * `tag_ids/id`) still holds references of that relation.
     */
    get comodel() {
        const fieldInfo = this.props.fieldInfo;
        if (fieldInfo.type === "id") {
            return fieldInfo.fieldPath.includes("/") ? fieldInfo.model_name : undefined;
        }
        return RELATIONAL_TYPES.includes(fieldInfo.type) ? fieldInfo.comodel_name : undefined;
    }

    get isRelational() {
        return Boolean(this.comodel);
    }

    get choices() {
        return (this.props.error.selection || []).map((choice) => ({
            value: choice.value,
            label: choice.display_name,
        }));
    }

    get canCorrectValue() {
        return this.props.error.value !== undefined;
    }

    get isFreeValue() {
        return !this.isRelational && this.choices.length === 0;
    }

    get canBeEmpty() {
        return (
            this.canCorrectValue && this.props.error.value !== "" && !this.props.fieldInfo.required
        );
    }

    get canCreate() {
        return ["many2one", "many2many"].includes(this.props.fieldInfo.type);
    }

    get isPicking() {
        return this.state.isPicking || this.resolution.action === "set";
    }

    get setValueLabel() {
        return this.isRelational ? _t("Set a record") : _t("Set a value");
    }

    get matchSources() {
        const matches = this.props.error.matches;
        if (!matches?.length) {
            return [];
        }
        return [
            {
                options: (request) =>
                    matches
                        .filter(
                            (match) =>
                                !request ||
                                match.display_name.toLowerCase().includes(request.toLowerCase())
                        )
                        .map((match) => ({
                            label: match.display_name,
                            onSelect: () => this.setValue(match.id, match.display_name),
                        })),
            },
        ];
    }

    /**
     * Picking the chosen resolution again takes it back.
     */
    toggle(action) {
        const isChosen = action === "set" ? this.isPicking : this.resolution.action === action;
        this.state.isPicking = !isChosen && action === "set";
        this.props.onResolve(this.props.error, isChosen || action === "set" ? false : { action });
    }

    setValue(value, displayName) {
        this.state.isPicking = true;
        this.props.onResolve(this.props.error, {
            action: "set",
            value,
            display_name: displayName,
        });
    }

    async quickCreate(name) {
        const [resId, displayName] = await this.orm.call(this.comodel, "name_create", [name]);
        this.setValue(resId, displayName);
    }

    async onRecordSelected(records) {
        const [record] = records || [];
        if (!record) {
            return;
        }
        let displayName = record.display_name;
        if (!displayName) {
            // a record created through "Create and edit..." is only given back by id
            [{ display_name: displayName }] = await this.orm.read(
                this.comodel,
                [record.id],
                ["display_name"]
            );
        }
        this.setValue(record.id, displayName);
    }
}
