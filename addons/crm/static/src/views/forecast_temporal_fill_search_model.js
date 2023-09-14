import { ForecastSearchModel } from "./forecast_search_model";

/**
 * Same as forecast search model but with the option to expand the search.
 */

export class ForecastTemporalFillSearchModel extends ForecastSearchModel {
    expandTemporalFilter() {
        this.fillTemporalPeriod().expand();
        this.updateTemporalFilter();
    }

    /**
     * @override
     */
    updateTemporalFilter() {
        const domain = this.fillTemporalPeriod().getDomain({ domain: [] });
        const context = this.fillTemporalPeriod().getContext({ context: {}, forceFillingTo: true });
        this.setTemporalFilter(domain, context);
    }
}
