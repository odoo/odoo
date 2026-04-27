import { patch } from "@web/core/utils/patch";
import { ProjectProfitabilitySection } from "@sale_project/components/project_right_side_panel/components/project_profitability_section";

patch(ProjectProfitabilitySection.prototype, {
    _getOrmValue(offset, section_id) {
        if (section_id === "subscriptions") {
            return {
                function: "get_subscription_items_data",
                args: [this.props.projectId, offset, 5],
            };
        } else {
            return super._getOrmValue(offset, section_id);
        }
    },
});
