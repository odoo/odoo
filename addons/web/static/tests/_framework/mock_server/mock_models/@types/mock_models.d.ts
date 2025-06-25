declare module "mock_models" {
    import { IrModelFields as IrModelFields2 } from "@web/../tests/_framework/mock_server/mock_models/ir_model_fields";
    import { ResGroups as ResGroups2 } from "@web/../tests/_framework/mock_server/mock_models/res_groups";

    export interface IrModelFields extends IrModelFields2 {}
    export interface ResGroups extends ResGroups2 {}

    export interface Models {
        "ir.model.fields": IrModelFields,
        "res.groups": ResGroups,
    }
}
