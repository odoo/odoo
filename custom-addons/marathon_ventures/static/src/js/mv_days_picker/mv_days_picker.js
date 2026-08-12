/** @odoo-module **/
/*  Bundle Pricing Days Picker (Many2many field widget).
 *
 *  Renders every day tag (mv.days.tag / mv.days_allowed.tag) as a
 *  checkbox with a Select All row on top. Reads and writes the
 *  Many2many field passed in via `props.name`; no new database field
 *  is introduced.
 *
 *  Behavior:
 *    * Ticking "Select All" checks every day.
 *    * Unticking any individual day when "Select All" was ticked
 *      unticks "Select All".
 *    * Ticking every individual day auto-ticks "Select All".
 *    * Unticking "Select All" while every day is checked unchecks
 *      every day.
 */
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class MvDaysPickerField extends Component {
    static template = "marathon_ventures.MvDaysPicker";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            options: [],   // [{id, name, checked}]
            loading: true,
        });
        onWillStart(async () => await this._load(this.props));
        onWillUpdateProps(async (nextProps) => await this._load(nextProps));
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------
    async _load(props) {
        const field = props.record.fields[props.name];
        const comodel = field.relation;               // 'mv.days.tag'
        // Load every option once; the set is tiny (7 records).
        const options = await this.orm.searchRead(
            comodel, [], ["id", "name"], { order: "id asc" },
        );
        const selectedIds = new Set(this._currentIds(props));
        this.state.options = options.map((o) => ({
            id: o.id,
            name: o.name,
            checked: selectedIds.has(o.id),
        }));
        this.state.loading = false;
    }

    _currentIds(props) {
        // In Odoo 17+ the record's data for a Many2many surfaces as an
        // object with `.records` (an array of DataPoints) or `.currentIds`.
        // We defensively try both shapes.
        const val = props.record.data[props.name];
        if (!val) {
            return [];
        }
        if (Array.isArray(val)) {
            return val.map((r) => (typeof r === "number" ? r : r.resId ?? r.id));
        }
        if (val.currentIds) {
            return [...val.currentIds];
        }
        if (val.resIds) {
            return [...val.resIds];
        }
        if (val.records) {
            return val.records.map((r) => r.resId);
        }
        return [];
    }

    // ------------------------------------------------------------------
    // Derived state
    // ------------------------------------------------------------------
    get allChecked() {
        return this.state.options.length > 0
            && this.state.options.every((o) => o.checked);
    }

    get someChecked() {
        return this.state.options.some((o) => o.checked)
            && !this.state.options.every((o) => o.checked);
    }

    // ------------------------------------------------------------------
    // Handlers
    // ------------------------------------------------------------------
    async onToggleAll(ev) {
        const checked = ev.target.checked;
        for (const opt of this.state.options) {
            opt.checked = checked;
        }
        await this._commit();
    }

    async onToggle(opt, ev) {
        opt.checked = ev.target.checked;
        await this._commit();
    }

    async _commit() {
        const ids = this.state.options.filter((o) => o.checked).map((o) => o.id);
        // Odoo 17+ Many2many update via record.update takes command tuples.
        // [6, 0, [ids]] = REPLACE-WITH.
        try {
            await this.props.record.update({
                [this.props.name]: [[6, 0, ids]],
            });
        } catch (e) {
            // Fallback for older command shapes: some builds accept
            // { operation, resIds }.
            await this.props.record.update({
                [this.props.name]: { operation: "REPLACE_WITH", resIds: ids },
            });
        }
    }
}

registry.category("fields").add("mv_days_picker", {
    component: MvDaysPickerField,
    supportedTypes: ["many2many"],
});
