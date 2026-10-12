declare module "mock_models" {
    import { webModels } from "@web/../tests/web_test_helpers";

    export interface IrModelFields extends webModels.IrModelFields {}
    export interface IrModuleCategory extends webModels.IrModuleCategory {}
    export interface ResGroups extends webModels.ResGroups {}
    export interface ResGroupsPrivilege extends webModels.ResGroupsPrivilege {}

    export interface Models {
        "ir.model.fields": IrModelFields;
        "ir.module.category": IrModuleCategory;
        "res.groups": ResGroups;
        "res.groups.privilege": ResGroupsPrivilege;
    }
}
