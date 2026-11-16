import { RelationalModel } from "@web/model/relational_model/relational_model";

/**
 * The hierarchy view only displays the records matching the domain: the links
 * between them are deduced, by the renderer, from the parent field.
 */
export class HierarchyModel extends RelationalModel {
    setup(params, services) {
        super.setup(params, services);
        this.parentFieldName = params.parentFieldName;
        this.childFieldName = params.childFieldName;
    }
}
