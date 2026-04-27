/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { Wysiwyg } from '@web_editor/js/wysiwyg/wysiwyg';
import { preserveCursor, closestElement } from '@web_editor/js/editor/odoo-editor/src/OdooEditor';
import { patch } from "@web/core/utils/patch";
import { Component } from "@odoo/owl";

patch(Wysiwyg.prototype, {
    _getPowerboxOptions() {
        const options = super._getPowerboxOptions(...arguments);
        const {commands, categories} = options;
        categories.push({ name: _t('Navigation'), priority: 40 });
        commands.push(
            {
                category: _t('Navigation'),
                name: _t('Appointment'),
                priority: 10,
                description: _t('Add a specific appointment'),
                fontawesome: 'fa-calendar',
                callback: async () => {
                    const selection = this.odooEditor.document.getSelection();
                    const anchorNode = selection && selection.anchorNode;
                    const restoreSelection = preserveCursor(this.odooEditor.document);
                    Component.env.services.dialog.add(AppointmentFormViewDialog, {
                        resModel: 'appointment.invite',
                        context: {
                            form_view_ref: "appointment.appointment_invite_view_form_insert_link",
                            default_appointment_type_ids: [],
                            default_staff_user_ids: [],
                        },
                        size: 'md',
                        title: _t("Insert Appointment Link"),
                        mode: "edit",
                        insertLink: (url) => {
                            this.focus();
                            restoreSelection();
                            const label = _t('Schedule an Appointment');
                            const existingLink = closestElement(anchorNode, 'a');
                            if (existingLink) {
                                existingLink.setAttribute('href', url);
                                existingLink.textContent = label;
                                this.odooEditor.historyStep();
                            } else {
                                const link = document.createElement('a');
                                link.setAttribute('href', url);
                                link.textContent = label;
                                this.odooEditor.execCommand('insert', link);
                            }
                        },
                    });
                },
            },
        );
        return {...options, commands, categories};
    }
});

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
