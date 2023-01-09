/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

export function useModelField() {
    const view = useService("view");

    const loadModelFields = (resModel) => {
        return view.loadFields(resModel, {
            attributes: [
                "store",
                "searchable",
                "type",
                "string",
                "relation",
                "selection",
                "related",
            ],
        });
    };

    const loadChain = async (resModel, fieldName) => {
        const fieldNameChain = fieldName.length ? fieldName.split(".") : [];
        let currentNode = {
            resModel,
            field: null,
        };
        const chain = [currentNode];
        for (const fieldName of fieldNameChain) {
            const fieldsInfo = await loadModelFields(currentNode.resModel);
            Object.assign(currentNode, {
                field: { ...fieldsInfo[fieldName], name: fieldName },
            });
            if (fieldsInfo[fieldName].relation) {
                currentNode = {
                    resModel: fieldsInfo[fieldName].relation,
                    field: null,
                };
                chain.push(currentNode);
            }
        }
        return chain;
    };

    return {
        loadModelFields,
        loadChain,
    };
}
