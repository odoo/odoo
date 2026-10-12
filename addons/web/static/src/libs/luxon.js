// @odoo-module ignore

// The following prevents luxon objects from being made reactive by Owl, because they are immutable
luxon.DateTime.prototype[Symbol.toStringTag] = "LuxonDateTime";
luxon.Duration.prototype[Symbol.toStringTag] = "LuxonDuration";
luxon.Interval.prototype[Symbol.toStringTag] = "LuxonInterval";
luxon.Settings.prototype[Symbol.toStringTag] = "LuxonSettings";
luxon.Info.prototype[Symbol.toStringTag] = "LuxonInfo";
luxon.Zone.prototype[Symbol.toStringTag] = "LuxonZone";
