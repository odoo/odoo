import { addFakeModel, addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";


addModelNamesToFetch(["resource.resource"]);

addFakeModel("resource.task", {
    display_name: { string: "Name", type: "char" },
    resource_ids: { string: "Resources", type: "many2many", relation: "resource.resource" },
    resource_id: { string: "Resource", type: "many2one", relation: "resource.resource" },
    resource_type: { string: "Resource Type", type: "char" },
});
