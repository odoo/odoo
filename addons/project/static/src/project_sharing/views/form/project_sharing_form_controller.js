/** @odoo-module */

<<<<<<< HEAD
||||||| parent of 1ad8dc291c49 (temp)
import { useService } from '@web/core/utils/hooks';
import { createElement } from "@web/core/utils/xml";
=======
import { _t } from "@web/core/l10n/translation";
import { useService } from '@web/core/utils/hooks';
import { createElement } from "@web/core/utils/xml";
>>>>>>> 1ad8dc291c49 (temp)
import { FormController } from '@web/views/form/form_controller';
<<<<<<< HEAD
||||||| parent of 1ad8dc291c49 (temp)
import { useViewCompiler } from '@web/views/view_compiler';
import { ProjectSharingChatterCompiler } from './project_sharing_form_compiler';
import { ChatterContainer } from '../../components/chatter/chatter_container';
=======
import { useViewCompiler } from '@web/views/view_compiler';
import { ProjectSharingChatterCompiler } from './project_sharing_form_compiler';
import { ChatterContainer } from '../../components/chatter/chatter_container';
import { useExternalListener } from "@odoo/owl";
>>>>>>> 1ad8dc291c49 (temp)

export class ProjectSharingFormController extends FormController {
<<<<<<< HEAD
    static components = {
        ...FormController.components,
    };
||||||| parent of 1ad8dc291c49 (temp)
    setup() {
        super.setup();
        this.uiService = useService('ui');
        const { xmlDoc } = this.archInfo;
        const template = createElement('t');
        const xmlDocChatter = xmlDoc.querySelector("div.oe_chatter");
        if (xmlDocChatter && xmlDocChatter.parentNode.nodeName === "form") {
            template.appendChild(xmlDocChatter.cloneNode(true));
        }
        const mailTemplates = useViewCompiler(ProjectSharingChatterCompiler, { Mail: template });
        this.mailTemplate = mailTemplates.Mail;
    }
=======
    setup() {
        super.setup();
        this.uiService = useService('ui');
        this.notification = useService('notification');
        const { xmlDoc } = this.archInfo;
        const template = createElement('t');
        const xmlDocChatter = xmlDoc.querySelector("div.oe_chatter");
        if (xmlDocChatter && xmlDocChatter.parentNode.nodeName === "form") {
            template.appendChild(xmlDocChatter.cloneNode(true));
        }
        const mailTemplates = useViewCompiler(ProjectSharingChatterCompiler, { Mail: template });
        this.mailTemplate = mailTemplates.Mail;
        useExternalListener(window, "paste", this.onGlobalPaste, { capture: true });
        useExternalListener(window, "drop", this.onGlobalDrop, { capture: true });
    }
>>>>>>> 1ad8dc291c49 (temp)

    get actionMenuItems() {
        return {};
    }

    get translateAlert() {
        return null;
    }

    onGlobalPaste(ev) {
        ev.preventDefault();
        if (ev.target.closest('.o_field_widget[name="description"]')) {
            const items = ev.clipboardData.items;
            for (let i = 0; i < items.length; i++) {
                if (items[i].type.indexOf('image') !== -1 && !this.model.root.resId) {
                    this.notification.add(
                        _t("Save the task to be able to paste images in description"),
                        { type: 'warning' },
                    )
                    ev.stopImmediatePropagation();
                    return;
                }
            }
        }
    }

    onGlobalDrop(ev) {
        ev.preventDefault();
        if (ev.target.closest('.o_field_widget[name="description"]')) {
            if(ev.dataTransfer.files.length > 0 && !this.model.root.resId){
                this.notification.add(
                    _t("Save the task to be able to drag images in description"),
                    { type: 'warning' },
                )
                ev.stopImmediatePropagation();
            }
        }
    }
}
