/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { _t } from "@web/core/l10n/translation";

import { Component, onWillStart } from "@odoo/owl";

export class ModelSelector extends Component {
    setup() {
        this.orm = useService("orm");

        onWillStart(async () => {
            if (!this.props.models) {
                this.models = await this._fetchAvailableModels();
            } else {
                this.models = await this.orm.call("ir.model", "display_name_for", [
                    this.props.models,
                ]);
            }

            this.models = this.models.map((record) => ({
                label: record.display_name,
                technical: record.model,
                classList: {
                    [`o_model_selector_${record.model}`]: 1,
                },
            }));
        });
    }

    get placeholder() {
        return _t("Type a model here...");
    }

    get sources() {
        return [this.optionsSource];
    }
    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
        };
    }

    onSelect(option) {
        this.props.onModelSelected({
            label: option.label,
            technical: option.technical,
        });
    }

    filterModels(name) {
        if (!name) {
            const visibleModels = this.models.slice(0, 8);
            if (this.models.length - visibleModels.length > 0) {
                visibleModels.push({
                    label: _t("Start typing..."),
                    unselectable: true,
                    classList: "o_m2o_start_typing",
                });
            }
            return visibleModels;
        }
        return fuzzyLookup(name, this.models, (model) => model.technical + model.label);
    }

    loadOptionsSource(request) {
        const options = this.filterModels(request);

        if (!options.length) {
            options.push({
                label: _t("No records"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }
        return options;
    }

    /**
     * Fetch the list of the models that can be
     * selected for the relational properties.
     */
    async _fetchAvailableModels() {
        const result = await this.orm.call("ir.model", "get_available_models");
        return result || [];
    }
}

ModelSelector.template = "web.ModelSelector";
ModelSelector.components = { AutoComplete };
ModelSelector.props = {
    onModelSelected: Function,
    id: { type: String, optional: true },
    value: { type: String, optional: true },
    // list of models technical name, if not set
    // we will fetch all models we have access to
    models: { type: Array, optional: true },
};
