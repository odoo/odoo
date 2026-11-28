import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

/**
 * Enterprise AccountReportFilterExtraOptions:
 * Draft Entries, Unfold All | Hide lines at 0 (BS + P&L), Split Horizontally (BS only).
 */
export class FsReportFilterExtraOptions extends Component {
    static template = "account_fs_report.FsReportFilterExtraOptions";
    static components = { Dropdown, DropdownItem };
    props = useProps({
        allEntries: t.boolean(),
        unfoldAll: t.boolean(),
        hide0Lines: t.boolean(),
        horizontalSplit: t.boolean().optional(false),
        showHorizontalSplit: t.boolean().optional(false),
        onToggleDraftEntries: t.function(),
        onToggleUnfoldAll: t.function(),
        onToggleHide0Lines: t.function(),
        onToggleHorizontalSplit: t.function().optional(),
    });

    get selectedExtraOptions() {
        return this.props.allEntries ? _t("With Draft Entries") : _t("Posted Entries");
    }
}
