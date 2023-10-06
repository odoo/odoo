import { registry } from "@web/core/registry";

import {
    DynamicModelFieldSelectorChar,
    dynamicModelFieldSelectorChar,
} from "@web/views/fields/dynamic_widget/dynamic_model_field_selector_char";

class CardCampaignElementFieldSelector extends DynamicModelFieldSelectorChar {
    filter(fieldDef) {
        if (this.props.record?.data?.render_type === "image") {
            if (!fieldDef.relation && fieldDef.type !== "binary") {
                return false;
            }
        } else {
            if (fieldDef.type === "binary") {
                return false;
            }
        }
        return super.filter(...arguments);
    }
}

const fieldDefinition = {
    ...dynamicModelFieldSelectorChar,
    component: CardCampaignElementFieldSelector,
};
registry.category("fields").add("CardCampaignElementFieldSelector", fieldDefinition);
