import { visitXML } from "@web/core/utils/xml";
import { stringToOrderBy } from "@web/search/utils/order_by";
import { CardArchParser } from "@web/views/card/card_arch_parser";


export class HierarchyArchParser {
    parse(xmlDoc, models, modelName) {
        const cardArchInfo = new CardArchParser().parse(xmlDoc, models, modelName);

        const archInfo = {
            ...cardArchInfo,
            cardArchInfo,
            defaultOrder: stringToOrderBy(xmlDoc.getAttribute("default_order") || null),
        };
        
        const fields = models[modelName].fields;

        visitXML(xmlDoc, (node) => {
            if (node.tagName === "hierarchy") {
                if (node.hasAttribute("child_field")) {
                    const childFieldName = node.getAttribute("child_field");
                    if (!(childFieldName in fields)) {
                        throw new Error(`The child field set (${childFieldName}) is not defined in the model (${modelName}).`);
                    } else if (fields[childFieldName].type !== "one2many") {
                        throw new Error(`Invalid child field, it should be a One2Many field.`);
                    } else if (fields[childFieldName].relation !== modelName) {
                        throw new Error(`Invalid child field, the co-model should be same model than the current one (expected: ${modelName}).`);
                    }
                    archInfo.childFieldName = childFieldName;
                    archInfo.parentFieldName = fields[childFieldName].relation_field;
                }
            }
        });

        if (!archInfo.childFieldName) {
            throw new Error('A valid child field (type: one2many) is required.');
        }

        return archInfo;
    }
}
