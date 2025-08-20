import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";

const HOUR_OPTION = { id: "hour", description: _t("Hour"), groupNumber: 1 };

export class PosSearchModel extends SearchModel {
    _models() {
        return {
            "pos.order": ["date_order"],
            "report.pos.order": ["date"],
        };
    }

    _getIntervalOptions(searchItem) {
        const intervalOptions = super._getIntervalOptions(searchItem);
        if (
            this.resModel in this._models() &&
            this._models()[this.resModel].includes(searchItem.fieldName)
        ) {
            return [...intervalOptions, HOUR_OPTION];
        }
        return intervalOptions;
    }

    _getIntervalOptionByIntervalId(intervalId) {
        if (this.resModel in this._models() && intervalId === HOUR_OPTION.id) {
            return HOUR_OPTION;
        }
        return super._getIntervalOptionByIntervalId(intervalId);
    }

    _rankInterval(intervalOptionId) {
        if (this.resModel in this._models() && intervalOptionId === HOUR_OPTION.id) {
            return super._rankInterval("day") + 1;
        }
        return super._rankInterval(intervalOptionId);
    }
}
