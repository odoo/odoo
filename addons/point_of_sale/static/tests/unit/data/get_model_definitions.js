import { registry } from "@web/core/registry";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { getPosModelDefinitions } from "./generate_model_definitions";

let definedModels = null;

export const getRelatedModelsParams = () => getPosModelDefinitions();
export const getRelatedModelsInstance = (useModelClass = true) => {
    if (definedModels) {
        return definedModels.models;
    }

    const { relations } = getPosModelDefinitions();
    const options = new DataServiceOptions();
    const modelClasses = {};

    for (const posModel of registry.category("pos_available_models").getAll()) {
        const pythonModel = posModel.pythonModel;
        const extraFields = posModel.extraFields || {};

        modelClasses[pythonModel] = posModel;
        relations[pythonModel] = {
            ...relations[pythonModel],
            ...extraFields,
        };
    }

    definedModels = createRelatedModels(relations, useModelClass ? modelClasses : {}, options);
    return definedModels.models;
};
