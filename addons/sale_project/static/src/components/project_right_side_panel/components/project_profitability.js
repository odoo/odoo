import { patch } from "@web/core/utils/patch";
import { ProjectProfitability } from "@project/components/project_right_side_panel/components/project_profitability";
import { ProjectProfitabilitySection } from "@sale_project/components/project_right_side_panel/components/project_profitability_section";

patch(ProjectProfitability, {
    props: {
        ...ProjectProfitability.props,
        projectId: Number,
        context: Object,
    },

    components: {
        ...ProjectProfitability.components,
        ProjectProfitabilitySection,
    },
});
