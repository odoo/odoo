import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { SkillsPivotModel } from "./skills_pivot_model";
import { SkillsPivotRenderer } from "./skills_pivot_renderer.js";

const viewRegistry = registry.category("views");

export const skillsPivotModel = {
    ...pivotView,
    Renderer: SkillsPivotRenderer,
    Model: SkillsPivotModel,
};

viewRegistry.add("skills_pivot_view", skillsPivotModel);
