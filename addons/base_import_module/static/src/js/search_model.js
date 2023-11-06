/** @odoo-module **/

import { SearchModel } from "@web/search/search_model";

/**
 * This is the conversion of ForecastModelExtension. See there for more
 * explanations of what is done here.
 */

export class ModuleSearchModel extends SearchModel {


    getSections(predicate) {
        let result = super.getSections(...arguments);
        let moduleType = result.find(s => {return s.fieldName == 'module_type'})
        if (moduleType){
            if (moduleType.rootIds[0] == false){
                moduleType.rootIds.shift()
                moduleType.activeValueId = moduleType.rootIds[0]
            }
            moduleType.values.delete(false)
        }
        return result
    }
    
}