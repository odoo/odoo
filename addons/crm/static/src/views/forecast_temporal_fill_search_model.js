import { ForecastSearchModel } from "./forecast_search_model";

/**
 * Same as forecast search model but forces filled computed end
 */

export class ForecastTemporalFillSearchModel extends ForecastSearchModel {
    /**
     * @override
     */
    _updateTemporalFilterPreHook() {
        this.unsetTemporalEnd();
    }
    /**
     * @override
     */
    updateTemporalFilter() {
        return super.updateTemporalFilter(true);
    }
}
