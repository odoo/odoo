import { onWillStart, useEffect } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormControllerWithHTMLExpander } from '@resource/views/form_with_html_expander/form_controller_with_html_expander'
import { ProjectTemplateDropdown } from "../components/project_template_dropdown";

function normalizeId(val) {
    if (!val) return false;
    if (Array.isArray(val)) {
        val = val.length > 0 ? val[0] : false;
    }
    if (val && typeof val === "object" && "id" in val) {
        return val.id;
    }
    return val || false;
}

export class ProjectProjectFormController extends FormControllerWithHTMLExpander {
    static template = "project.ProjectFormView";
    static components = {
        ...FormControllerWithHTMLExpander.components,
        ProjectTemplateDropdown,
    };
    static props = {
        ...FormControllerWithHTMLExpander.props,
        focusTitle: {
            type: Boolean,
            optional: true,
        },
    };
    static defaultProps = {
        ...FormControllerWithHTMLExpander.defaultProps,
        focusTitle: false,
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
        });

        if (this.props.focusTitle) {
            useEffect(
                (el) => {
                    if (el) {
                        const title = this.rootRef.el.querySelector("#name_0");
                        if (title) {
                            title.focus();
                        }
                    }
                },
                () => [this.rootRef.el]
            );
        }
    }

    async onWillSaveRecord(record, changes) {
        const prevAccountId = normalizeId(record._values.account_id);
        const newAccountId = "account_id" in changes
            ? normalizeId(changes.account_id)
            : prevAccountId;

        const timesheetsEnabled = "allow_timesheets" in changes
            ? changes.allow_timesheets
            : record._values.allow_timesheets ?? false;

        const isAccountRemoved = !!prevAccountId && !newAccountId;

        if (isAccountRemoved && timesheetsEnabled) {
            const confirmed = await new Promise(resolve => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Confirm Disabling Timesheets"),
                    body: _t(
                        "The Timesheets feature requires an analytic account for the Project plan. Removing it will disable the feature. Are you sure you want to continue?"
                    ),
                    confirmLabel: _t("Proceed"),
                    cancelLabel: _t("Cancel"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });

            if (confirmed) {
                changes.allow_timesheets = false;
            } else {
                return false;
            }
        }
        return super.onWillSaveRecord(...arguments);
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.isAvailable = () => this.isProjectManager;
        }
        return actionMenuItems;
    }
}
