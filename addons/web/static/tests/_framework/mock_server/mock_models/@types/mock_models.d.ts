declare module "mock_models" {
    import { webModels } from "@web/../tests/web_test_helpers";

    export interface IrModelFields extends webModels.IrModelFields {}
    export interface ResGroups extends webModels.ResGroups {}

    export interface Models {
        "ir.model.fields": IrModelFields;
        "res.groups": ResGroups;
    }
}
