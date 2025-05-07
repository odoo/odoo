import { _t } from "@web/core/l10n/translation";
import { PivotModel } from "@web/views/pivot/pivot_model";

export class DiscussChannelPivotModel extends PivotModel {
    _prepareData(group, groupSubdivisions, config) {
        for (const groupSubdivision of groupSubdivisions) {
            if (groupSubdivision.rowGroupBy?.[0] === "rating_last_value") {
                groupSubdivision.subGroups.forEach((subGroup) => {
                    switch (subGroup.rating_last_value) {
                        case 0:
                            subGroup.rating_last_value = _t("Unrated");
                            break;
                        case 1:
                            subGroup.rating_last_value = _t("Unhappy");
                            break;
                        case 3:
                            subGroup.rating_last_value = _t("Neutral");
                            break;
                        case 5:
                            subGroup.rating_last_value = _t("Happy");
                            break;
                    }
                });
            }
        }
        super._prepareData(group, groupSubdivisions, config);
    }
}
