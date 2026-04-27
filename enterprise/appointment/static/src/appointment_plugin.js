import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

class AppointmentFormViewDialog extends FormViewDialog {
    static props = {
        ...FormViewDialog.props,
        insertLink: { type: Function },
    };
    setup() {
        super.setup();
        this.viewProps.insertLink = this.props.insertLink;
        this.viewProps.closeDialog = this.props.close;
    }
}

class AppointmentPlugin extends Plugin {
    static id = "appointment";
    static dependencies = ["selection", "link", "dialog"];
     resources = {
        user_commands: [
            {
                id: "insertAppointment",
                title: _t("Appointment"),
                description: _t("Add a specific appointment"),
                icon: "fa-calendar",
                run: this.addAppointment.bind(this),
            },
        ],
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "insertAppointment",
            },
        ],
    };

    addAppointment() {
        this.dependencies.dialog.addDialog(AppointmentFormViewDialog, {
            resModel: "appointment.invite",
            context: {
                form_view_ref: "appointment.appointment_invite_view_form_insert_link",
                default_appointment_type_ids: [],
                default_staff_user_ids: [],
            },
            size: "md",
            title: _t("Insert Appointment Link"),
            mode: "edit",
            insertLink: (url) =>
                this.dependencies.link.insertLink(url, _t("Schedule an Appointment")),
        });
    }
}

// add appointment plugin for all standard use cases
MAIN_PLUGINS.push(AppointmentPlugin);
