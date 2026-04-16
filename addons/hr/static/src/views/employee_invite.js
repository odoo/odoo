import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ListRenderer } from "@web/views/list/list_renderer";
import { Component, onWillStart, proxy } from "@odoo/owl";
import { HrEmployeeKanbanController, HrEmployeeKanbanRenderer } from "@hr/views/hr_kanban_view";
import { EmployeeListController } from "@hr/views/hr_list_view";

const INVITE_ACTION = "hr.hr_invitation_link_action_new";

/** Banner listing the active invitation links, shown on top of the employee views. */
export class InvitationLinksBanner extends Component {
    static template = "hr.InvitationLinksBanner";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = proxy({ links: [] });
        onWillStart(() => this.loadLinks());
    }

    async loadLinks() {
        try {
            this.state.links = await this.orm.searchRead(
                "hr.invitation.link",
                [["active", "=", true]],
                ["display_name", "url", "used_count", "max_uses"],
                { limit: 20 },
            );
        } catch {
            // Non-HR users have no access to invitation links: just hide the banner.
            this.state.links = [];
        }
    }

    usageLabel(link) {
        return link.max_uses ? `${link.used_count} / ${link.max_uses}` : `${link.used_count}`;
    }

    async copyUrl(link) {
        await browser.navigator.clipboard.writeText(link.url);
        this.notification.add(_t("Invitation link copied to clipboard."), { type: "success" });
    }

    editLink(link) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "hr.invitation.link",
                res_id: link.id,
                views: [[false, "form"]],
                target: "new",
            },
            { onClose: () => this.loadLinks() },
        );
    }

    deleteLink(link) {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete invitation link"),
            body: _t("This link will no longer let anyone register. Continue?"),
            confirmLabel: _t("Delete"),
            confirm: async () => {
                await this.orm.unlink("hr.invitation.link", [link.id]);
                await this.loadLinks();
            },
            cancel: () => {},
        });
    }
}

/** Mixin adding the "Invite" control-panel button to an employee view controller. */
const EmployeeInviteController = (Base) => class extends Base {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }
    openInviteDialog() {
        this.actionService.doAction(INVITE_ACTION, {
            onClose: () => this.model.load(),
        });
    }
};

// The banner lives inside the renderer (the column next to the search panel) so
// it spans the full width above the records, in both kanban and list views.
export class EmployeeInviteKanbanRenderer extends HrEmployeeKanbanRenderer {
    static template = "hr.EmployeeInviteKanbanRenderer";
    static components = { ...HrEmployeeKanbanRenderer.components, InvitationLinksBanner };
}
export class EmployeeInviteListRenderer extends ListRenderer {
    static template = "hr.EmployeeInviteListRenderer";
    static components = { ...ListRenderer.components, InvitationLinksBanner };
}

export class EmployeeInviteKanbanController extends EmployeeInviteController(HrEmployeeKanbanController) {}
export class EmployeeInviteListController extends EmployeeInviteController(EmployeeListController) {}

const kanbanReg = registry.category("views").get("hr_employee_kanban");
registry.category("views").add("hr_employee_kanban", {
    ...kanbanReg,
    Controller: EmployeeInviteKanbanController,
    Renderer: EmployeeInviteKanbanRenderer,
    buttonTemplate: "hr.EmployeeKanbanButtons",
}, { force: true });

const listReg = registry.category("views").get("hr_employee_list");
registry.category("views").add("hr_employee_list", {
    ...listReg,
    Controller: EmployeeInviteListController,
    Renderer: EmployeeInviteListRenderer,
    buttonTemplate: "hr.EmployeeListButtons",
}, { force: true });
