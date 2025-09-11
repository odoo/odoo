import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { _t } from "@web/core/l10n/translation";

import { Component, onWillStart } from "@odoo/owl";

export class ModelSelector extends Component {
    static template = "web.ModelSelector";
    static components = { AutoComplete };
    static props = {
        onModelSelected: Function,
        id: { type: String, optional: true },
        value: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        // list of models technical name, if not set
        // we will fetch all models we have access to
        models: { type: Array, optional: true },
        nbVisibleModels: { type: Number, optional: true },
    };

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
                cssClass: `o_model_selector_${record.model.replaceAll(".", "_")}`,
                data: {
                    technical: record.model,
                },
                label: record.display_name,
                onSelect: () =>
                    this.props.onModelSelected({
                        label: record.display_name,
                        technical: record.model,
                    }),
            }));
        });
    }

    get sources() {
        return [this.optionsSource];
    }

    get placeholder() {
        return this.props.placeholder || _t("Type a model here...");
    }

    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
        };
    }

    get nbVisibleModels() {
        return this.props.nbVisibleModels || 8;
    }

    filterModels(name) {
        if (!name) {
            const visibleModels = this.models.slice(0, this.nbVisibleModels);
            if (this.models.length - visibleModels.length > 0) {
                visibleModels.push({
                    label: _t("Start typing..."),
                    cssClass: "o_m2o_start_typing",
                });
            }
            return visibleModels;
        }
        return fuzzyLookup(name, this.models, (model) => model.data.technical + model.label);
    }

    loadOptionsSource(request) {
        const options = this.filterModels(request);

        if (!options.length) {
            options.push({
                label: _t("No records"),
                cssClass: "o_m2o_no_result",
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
