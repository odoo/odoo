/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { zipWith } from "@web/core/utils/arrays";

export function useModelField() {
    const fieldService = useService("field");

    const loadModelFields = (resModel) => {
        return fieldService.loadFields(resModel);
    };

    const loadChain = async (resModel, path) => {
        if ("01".includes(path.toString())) {
            return [{ resModel, field: null }];
        }
        if (typeof path !== "string" || !path) {
            return [{ resModel, field: null }];
        }
        const { isInvalid, names, modelsInfo } = await fieldService.loadPath(resModel, path);
        if (isInvalid) {
            return [{ resModel, field: null }];
        }
        const chain = zipWith(names, modelsInfo, (name, { resModel, fieldDefs }) => {
            return { resModel, field: fieldDefs[name] };
        });
        const lastField = chain.at(-1)?.field;
        if (lastField.relation) {
            chain.push({ resModel: lastField.relation, field: null });
        }
        return chain;
    };

    return {
        loadModelFields,
        loadChain,
    };
}
