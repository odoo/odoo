/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class AnalyticAutoComplete extends AutoComplete {}
AnalyticAutoComplete.template = "analytic.AutoComplete";
AnalyticAutoComplete.props = {
    ...AutoComplete.props,
    onFocus: { type: Function, optional: true },
}
AnalyticAutoComplete.defaultProps = {
    ...AutoComplete.defaultProps,
    onFocus: () => {},
}
