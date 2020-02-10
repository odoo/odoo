// TODO Remove me >=saas-12.5, this is a disgrace
// This is an hack to get the string_* and hover_* options translated on the
// boolean_button terminology widget. The terms are translated through
// _t(opt_terms.string_true) which will only work if the terms are already
// present in the translation map.
// This code does nothing but marks the strings as translatable
var _t = function(x) { return x; };

_t("Production Environment");
_t("Switch to test environment");
_t("Test Environment");
_t("Switch to production environment");
_t("Debug requests");
_t("Disable debug");
_t("No debug");
_t("Enable debug");
