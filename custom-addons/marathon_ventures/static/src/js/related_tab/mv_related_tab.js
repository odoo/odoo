/** @odoo-module **/
/*  Related Tab (Phase 19)
 *  ------------------------------------------------------------
 *  Renders a Salesforce-style panel of every One2many / Many2many
 *  relationship defined on the current record's model.
 *
 *  Bound to the `id` field (Integer). Auto-injected on every
 *  mv.* form via the FormCompiler patch in mv_related_tab_inject.js.
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    Component, useState, onWillStart, onWillUpdateProps,
} from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";


// =========================================================================
// RELATED_TAB_COLUMNS - developer-controlled column map.
//
// Key: comodel technical name (e.g. "mv.deal", "mv.schedules").
// Value: ordered list of field names on that comodel to render in each
// preview row on the Related tab.
//
// Any comodel NOT listed here falls back to `display_name` only.
// Edit this map to add or remove columns; hard-refresh the browser
// (Ctrl+Shift+R) to pick up asset-bundle changes.
// =========================================================================
const RELATED_TAB_COLUMNS = {
    "mv.deal":      ["length"],
    "mv.schedules": ["rate", "week"],
};

export class MvRelatedTab extends Component {
    static template = "marathon_ventures.MvRelatedTab";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            error: "",
            specs: [],
        });
        onWillStart(this.reload.bind(this));
        // Reload when the caller navigates to a different record
        onWillUpdateProps((nextProps) => {
            const oldId = this.props.record && this.props.record.resId;
            const newId = nextProps.record && nextProps.record.resId;
            if (newId !== oldId) this.reload(newId);
        });
    }

    get modelName() {
        return this.props.record && this.props.record.resModel;
    }

    get resId() {
        return this.props.record && this.props.record.resId;
    }

    async reload(overrideId) {
        this.state.loading = true;
        this.state.error = "";
        try {
            const id = overrideId || this.resId;
            if (!id) {
                this.state.specs = [];
                return;
            }
            this.state.specs = await this.orm.call(
                "mv.related", "related_specs",
                [this.modelName, id, RELATED_TAB_COLUMNS], {},
            );
        } catch (e) {
            this.state.error = (e && e.data && e.data.message)
                || (e && e.message) || String(e);
            this.state.specs = [];
        } finally {
            this.state.loading = false;
        }
    }

    // ---- View All: open list of related records -------------------
    async onViewAll(spec) {
        if (!spec || !spec.accessible) return;
        // Build the domain the same way Odoo's own O2M "list all"
        // does for the two relationship flavours.
        let domain = [];
        if (spec.type === "one2many" && spec.inverse_name) {
            domain = [[spec.inverse_name, "=", this.resId]];
        } else {
            // Many2one lookup by the record's own m2m field ids
            // Fallback: fetch ids from the parent record's field
            // and use them in an IN clause. Works for both m2m
            // and o2m without an inverse name.
            let ids = [];
            try {
                const rec = await this.orm.read(
                    this.modelName, [this.resId], [spec.field_name],
                );
                if (rec && rec[0] && Array.isArray(rec[0][spec.field_name])) {
                    ids = rec[0][spec.field_name];
                }
            } catch (e) { /* swallow */ }
            domain = [["id", "in", ids]];
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: spec.label,
            res_model: spec.comodel,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    async onOpenRecord(spec, rec) {
        if (!rec || !rec.id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: spec.comodel,
            res_id: rec.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("fields").add("mv_related_tab", {
    component: MvRelatedTab,
    supportedTypes: ["integer"],
});
