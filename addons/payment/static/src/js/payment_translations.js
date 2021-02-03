// TODO Remove me >=saas-12.5, this is a disgrace
// This is an hack to get the string_true and hover_false options translated on
// the boolean_button terminology widget. The terms are translated through
// _t(opt_terms.string_true) which will only work if the terms are already
// present in the translation map.
// This code does nothing but marks the strings as translatable
var _t = function(x) { return x; };

_t("Published");
_t("Publish");
