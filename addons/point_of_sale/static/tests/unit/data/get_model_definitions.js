import { registry } from "@web/core/registry";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { MockServer } from "@web/../tests/web_test_helpers";

export const getModelDefinitions = () => {
    const session = MockServer.current._models["pos.session"];
    const params = session.load_data_params();
    return Object.entries(params).reduce((acc, [modelName, params]) => {
        acc[modelName] = params.relations;
        return acc;
    }, {});
};

let generatedModels = null;

export const getRelatedModelsInstance = (useModelClass = true) => {
    if (generatedModels) {
        return generatedModels;
    }

    const options = new DataServiceOptions();
    const relations = getModelDefinitions();
    const modelClasses = {};

    if (useModelClass) {
        for (const posModel of registry.category("pos_available_models").getAll()) {
            const pythonModel = posModel.pythonModel;
            const extraFields = posModel.extraFields || {};

            modelClasses[pythonModel] = posModel;
            relations[pythonModel] = {
                ...relations[pythonModel],
                ...extraFields,
            };
        }
    }

    const models = createRelatedModels(relations, useModelClass ? modelClasses : {}, options);
    generatedModels = models.models;
    return models.models;
};
