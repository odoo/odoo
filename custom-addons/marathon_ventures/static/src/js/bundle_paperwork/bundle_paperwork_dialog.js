/** @odoo-module **/
/*  Bundle Paperwork - OWL Dialog.
 *
 *  Entry point: registered as a client action under the tag
 *  "mv_bundle_paperwork_dialog". mv.deal.action_open_bundle_paperwork
 *  returns that tag with { deal_id } in params; the client action
 *  handler opens BundlePaperworkDialog through the dialog service.
 *
 *  UI (per the reference screenshot / requirement):
 *     [ Generate Paperwork (New Buy) ]
 *
 *     XML Files
 *       <file>.xml   [Send] [Regenerate]
 *       ...
 *
 *     Excel Files
 *       <file>.xlsx  [Send] [Bundle Action 1] [Bundle Action 2] ...
 *
 *  Clicking a Bundle Action opens BundleStartWeekDialog (mini OWL
 *  popup) to pick the Bundle Start Week, then calls the backend to
 *  execute the action.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";


// =========================================================================
// BundleStartWeekDialog - mini popup for Bundle Start Week
// =========================================================================
export class BundleStartWeekDialog extends Component {
    static template = "marathon_ventures.BundleStartWeekDialog";
    static components = { Dialog };
    static props = {
        close: { type: Function },        // supplied by dialog service
        actionCode: { type: String },
        actionLabel: { type: String },
        initialWeek: { type: String, optional: true },
        onSubmit: { type: Function },     // called with (isoDate)
    };

    setup() {
        this.state = useState({
            week: this.props.initialWeek || "",
            error: "",
        });
    }

    async onConfirm() {
        if (!this.state.week) {
            this.state.error = _t("Please pick a Bundle Start Week.");
            return;
        }
        this.state.error = "";
        try {
            await this.props.onSubmit(this.state.week);
            this.props.close();
        } catch (e) {
            this.state.error =
                (e && e.data && e.data.message)
                || (e && e.message) || String(e);
        }
    }

    onCancel() {
        this.props.close();
    }

    onWeekInput(ev) {
        this.state.week = ev.target.value || "";
    }
}


// =========================================================================
// BundlePaperworkDialog - main popup
// =========================================================================
export class BundlePaperworkDialog extends Component {
    static template = "marathon_ventures.BundlePaperworkDialog";
    static components = { Dialog };
    static props = {
        close: { type: Function },
        dealId: { type: Number },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            loading: true,
            busy: false,
            error: "",
            snapshot: {
                deal_name: "",
                brand: "",
                program: "",
                bundle_action: "",
                bundle_start_week: "",
                bundle_actions: [],
                xml_files: [],
                excel_files: [],
            },
        });

        onWillStart(async () => await this._loadState());
    }

    async _loadState() {
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.snapshot = await this.orm.call(
                "mv.deal", "bundle_paperwork_state", [[this.props.dealId]],
            );
        } catch (e) {
            this.state.error =
                (e && e.data && e.data.message)
                || (e && e.message) || String(e);
        } finally {
            this.state.loading = false;
        }
    }

    get title() {
        const snap = this.state.snapshot;
        if (snap && snap.deal_name) {
            return `Bundle Paperwork · ${snap.deal_name}`;
        }
        return "Bundle Paperwork";
    }

    // -------- Generate Paperwork (New Buy) -----------------------
    async onGenerate() {
        if (this.state.busy) return;
        this.state.busy = true;
        try {
            this.state.snapshot = await this.orm.call(
                "mv.deal", "bundle_paperwork_generate",
                [[this.props.dealId]],
            );
            const n =
                this.state.snapshot.xml_files.length +
                this.state.snapshot.excel_files.length;
            this.notification.add(
                _t("Generated %(n)s file(s).", { n }),
                { type: "success" },
            );
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message)
                || (e && e.message) || String(e),
                { type: "danger" },
            );
        } finally {
            this.state.busy = false;
        }
    }

    // -------- Per-file: Send -------------------------------------
    async onSend(file) {
        try {
            const action = await this.orm.call(
                "mv.deal", "bundle_paperwork_send",
                [[this.props.dealId], file.id],
            );
            await this.action.doAction(action);
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message)
                || (e && e.message) || String(e),
                { type: "danger" },
            );
        }
    }

    // -------- XML only: Regenerate -------------------------------
    async onRegenerate(file) {
        if (this.state.busy) return;
        this.state.busy = true;
        try {
            this.state.snapshot = await this.orm.call(
                "mv.deal", "bundle_paperwork_regenerate",
                [[this.props.dealId], file.id],
            );
            this.notification.add(
                _t("Regenerated %(name)s", { name: file.name }),
                { type: "success" },
            );
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message)
                || (e && e.message) || String(e),
                { type: "danger" },
            );
        } finally {
            this.state.busy = false;
        }
    }

    // -------- Excel: Bundle Action -> mini popup -----------------
    onBundleAction(action) {
        this.dialog.add(BundleStartWeekDialog, {
            actionCode: action.code,
            actionLabel: action.label,
            initialWeek: this.state.snapshot.bundle_start_week || "",
            onSubmit: async (weekIso) => {
                this.state.snapshot = await this.orm.call(
                    "mv.deal", "bundle_paperwork_run_action",
                    [[this.props.dealId], action.code, weekIso],
                );
                this.notification.add(
                    _t("Bundle action executed: %(l)s (week %(w)s)", {
                        l: action.label, w: weekIso,
                    }),
                    { type: "success" },
                );
            },
        });
    }

    // -------- Download URL (opens/downloads the file) ------------
    fileHref(fileId) {
        return `/web/content/${fileId}?download=true`;
    }
}


// =========================================================================
// Client-action registration
// =========================================================================
registry.category("actions").add(
    "mv_bundle_paperwork_dialog",
    (env, action) => {
        const dealId = action && action.params && action.params.deal_id;
        if (!dealId) {
            env.services.notification.add(
                _t("Bundle Paperwork: no Deal id supplied."),
                { type: "danger" },
            );
            return;
        }
        env.services.dialog.add(BundlePaperworkDialog, {
            dealId: Number(dealId),
        });
    },
);
