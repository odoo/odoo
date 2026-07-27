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
// RELATED_TAB_CONFIG - developer-controlled Related tab map.
//
// Explicit opt-in per parent model. A parent model that isn't a top-level
// key here shows an empty Related tab. Within each parent, list the
// COMODELS you want to expose and the columns to render on each preview
// row. Comodels can be reached either by:
//   * a direct One2many / Many2many field on the parent, OR
//   * an inverse Many2one on the comodel pointing back to the parent
//     (backend auto-detects and uses it as a virtual One2many).
//
// Shape:
//     "<parent.model>": {
//         "<comodel.name>": ["<column>", ...],
//         ...
//     }
//
// Edit + hard-refresh browser (Ctrl+Shift+R) to pick up changes.
// =========================================================================
const RELATED_TAB_CONFIG = {
    "mv.advertiser": {
        "mv.brands": []
    },
    "mv.brands": {
        "mv.deal": ['length']
    },
    "mv.deal": {
        "mv.schedules": ["rate", "week"],
        "mv.traffic":   [],
    },
    "mv.schedules": {
        "mv.spot_data":          [],
        "mv.spot_data_mirror":   [],
        "mv.prelog_data":        [],
        "mv.prelog_data_mirror": [],
    },
    "mv.traffic": {
        "mv.split": []
    }
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
                [this.modelName, id, RELATED_TAB_CONFIG], {},
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
