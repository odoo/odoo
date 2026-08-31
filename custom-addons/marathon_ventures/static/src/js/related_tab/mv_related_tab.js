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
    Component, useState, onWillStart, onWillUpdateProps, useRef,
} from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";


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
        // Bundle Paperwork files (linked via
        // mv.deal.bundle_paperwork_attachment_ids Many2many).
        "ir.attachment": ["name", "mv_bundle_paperwork_kind", "create_date"],
    },
    "mv.schedules": {
        "mv.spot_data":          [],
        "mv.spot_data_mirror":   [],
        "mv.prelog_data":        [],
        "mv.prelog_data_mirror": [],
    },
    "mv.traffic": {
        "mv.split": ["isci", "days_allowed", "active"]
    }
};

export class MvRelatedTab extends Component {
    static template = "marathon_ventures.MvRelatedTab";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.fileInputRef = useRef("fileInput");
        // Section that requested the next Attach File click. Set by
        // onAttachFile so onFilePicked knows where to route the upload.
        this._uploadSpec = null;
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
        // Polymorphic sections (ir.attachment via res_model/res_id)
        // don't have a field_name or an inverse M2O - build the
        // domain from the upload_res_model / upload_res_id the
        // backend spec carries.
        if (spec.type === "polymorphic" && spec.upload_res_model) {
            domain = [
                ["res_model", "=", spec.upload_res_model],
                ["res_id",    "=", spec.upload_res_id],
            ];
        } else if (spec.type === "one2many" && spec.inverse_name) {
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

    // ---- New <Label>: open FormViewDialog with parent auto-filled --
    onNewRecord(spec) {
        if (!spec || !spec.accessible || !spec.supports_create) return;
        // When we have an inverse M2O ('mv.split.traffic' -> mv.traffic),
        // pre-fill it so the user doesn't have to pick the parent.
        // For direct M2M/O2M relationships we can't safely default the
        // M2M value from context; the user picks / it's set on save.
        const context = {};
        if (spec.inverse_name && spec.parent_id) {
            context["default_" + spec.inverse_name] = spec.parent_id;
        }
        // dialog.add() returns a `close` callback we invoke explicitly
        // after the record is saved. The default FormViewDialog only
        // auto-closes when the user clicks its own "Save & Close"
        // button; if the record is saved via the mv.* Save button
        // injected by phase7 (mv.save.button.mixin) the dialog would
        // otherwise stay open. Capturing close here fixes that.
        const close = this.dialog.add(FormViewDialog, {
            resModel: spec.comodel,
            context: context,
            title: `New ${spec.label}`,
            onRecordSaved: async () => {
                await this.reload();
                if (typeof close === "function") {
                    close();
                }
            },
        });
    }

    // ---- Attach File: click a hidden <input type=file> --------------
    onAttachFile(spec) {
        if (!spec || !spec.supports_upload) return;
        if (!this.fileInputRef.el) return;
        this._uploadSpec = spec;
        // Reset value so picking the same file twice still fires
        // the change event.
        this.fileInputRef.el.value = "";
        this.fileInputRef.el.click();
    }

    async onFilePicked(ev) {
        const spec = this._uploadSpec;
        this._uploadSpec = null;
        const files = ev && ev.target && ev.target.files;
        if (!spec || !files || files.length === 0) return;
        try {
            for (const file of files) {
                const dataUrl = await this._readAsDataURL(file);
                // dataUrl is like "data:<mime>;base64,<payload>"
                const idx = dataUrl.indexOf(",");
                const b64 = idx >= 0 ? dataUrl.slice(idx + 1) : dataUrl;
                await this.orm.create("ir.attachment", [{
                    name: file.name || "Attachment",
                    datas: b64,
                    res_model: spec.upload_res_model,
                    res_id: spec.upload_res_id,
                    mimetype: file.type || false,
                    type: "binary",
                }]);
            }
            this.notification.add(
                files.length === 1
                    ? `Uploaded ${files[0].name}`
                    : `Uploaded ${files.length} files`,
                { type: "success" },
            );
            await this.reload();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || (e && e.message) || String(e),
                { type: "danger" },
            );
        } finally {
            // Clear the input so re-picking works.
            if (this.fileInputRef.el) this.fileInputRef.el.value = "";
        }
    }

    _readAsDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
        });
    }

    // ---- Delete an attachment row ----------------------------------
    async onDeleteRow(spec, rec) {
        if (!rec || !rec.id || !spec) return;
        if (!confirm(`Delete "${rec.display_name || rec.name || rec.id}"?`)) return;
        try {
            await this.orm.unlink(spec.comodel, [rec.id]);
            await this.reload();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || (e && e.message) || String(e),
                { type: "danger" },
            );
        }
    }
}

registry.category("fields").add("mv_related_tab", {
    component: MvRelatedTab,
    supportedTypes: ["integer"],
});
