// @ts-check

/** @module @web/components/model_selector/model_selector - Autocomplete component for searching and selecting Odoo model names */

import { Component, onWillStart } from "@odoo/owl";
import { AutoComplete } from "@web/components/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
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
        autofocus: { type: Boolean, optional: true },
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

    /** @returns {Object[]} autocomplete source descriptors */
    get sources() {
        return [this.optionsSource];
    }

    /** @returns {string} input placeholder text */
    get placeholder() {
        return this.props.placeholder || _t("Type a model here...");
    }

    /** @returns {{ placeholder: string, options: Function }} source descriptor with lazy option loading */
    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
        };
    }

    /** @returns {number} maximum models shown before "Start typing..." prompt */
    get nbVisibleModels() {
        return this.props.nbVisibleModels || 8;
    }

    /**
     * @param {string} name - search query to fuzzy-match against model names
     * @returns {Object[]} matching model options, possibly with a "Start typing..." hint
     */
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
        return fuzzyLookup(
            name,
            this.models,
            (model) => model.data.technical + model.label,
        );
    }

    /**
     * @param {string} request - user input text for filtering
     * @returns {Object[]} model options or a "No records" fallback
     */
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
     * Fetch the list of the models that can be selected for the relational properties.
     * @returns {Promise<Array<{model: string, display_name: string}>>}
     */
    async _fetchAvailableModels() {
        const result = await this.orm.call("ir.model", "get_available_models");
        return result || [];
    }
}
