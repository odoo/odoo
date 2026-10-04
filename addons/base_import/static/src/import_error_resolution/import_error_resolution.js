import { Component, proxy, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const RELATIONAL_TYPES = ["many2one", "many2many", "one2many"];

/**
 * Autocomplete listing first the records the offending value did match, as they
 * are the likeliest answer to an ambiguity, then the regular search.
 */
export class ImportMatchAutocomplete extends Many2XAutocomplete {
    get sources() {
        return [...this.props.otherSources, this.optionsSource];
    }
    addStartTypingSuggestion() {
        return false;
    }
}

/**
 * Ways out of a single import error, offered as selection badges: leave the
 * offending value out, or replace it by one the field accepts.
 *
 * As with any selection, the chosen way out can be changed by picking another
 * one, and taken back by picking it again.
 */
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
     * The model the records to pick from belong to. A column mapped on the
     * external or database id of a relation (e.g. `tag_ids/id`) still holds
     * references of that relation: the server resolves the record picked for
     * it just like for the relation itself.
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

    /**
     * The values a selection or boolean field accepts, as reported along with
     * the error.
     */
    get choices() {
        return (this.props.error.selection || []).map((choice) => ({
            value: choice.value,
            label: choice.display_name,
        }));
    }

    /**
     * Without the offending cell there is nothing to correct: the error can
     * only be reported, and has to be sorted out in the file itself.
     */
    get canCorrectValue() {
        return this.props.error.value !== undefined;
    }

    /**
     * Whatever the field accepts can be typed in, when it is neither a record
     * to search for nor one of a fixed set of values.
     */
    get isFreeValue() {
        return !this.isRelational && this.choices.length === 0;
    }

    /**
     * An empty value cannot be left out, and a required one must not be.
     */
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

    /**
     * Suggest the records the ambiguous value matched before anything else.
     */
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
     * Picking the chosen way out again takes it back, leaving the error to
     * block the import as it did before.
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
