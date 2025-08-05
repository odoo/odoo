import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { SkillsPivotModel } from "./skills_pivot_model";

const viewRegistry = registry.category("views");

export const skillsPivotModel = {
    ...pivotView,
    Model: SkillsPivotModel,
};

viewRegistry.add("skill_pivot_view", skillsPivotModel);
