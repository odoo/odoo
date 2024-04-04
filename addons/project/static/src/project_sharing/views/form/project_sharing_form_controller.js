/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { createElement } from "@web/core/utils/xml";
import { FormController } from '@web/views/form/form_controller';
import { useViewCompiler } from '@web/views/view_compiler';
import { ProjectSharingChatterCompiler } from './project_sharing_form_compiler';
import { ChatterContainer } from '../../components/chatter/chatter_container';

const { useExternalListener } = owl;

export class ProjectSharingFormController extends FormController {
    setup() {
        super.setup();
        this.uiService = useService('ui');
        const { arch, xmlDoc } = this.archInfo;
        const template = createElement('t');
        const xmlDocChatter = xmlDoc.querySelector("div.oe_chatter");
        if (xmlDocChatter && xmlDocChatter.parentNode.nodeName === "form") {
            template.appendChild(xmlDocChatter.cloneNode(true));
        }
        const mailTemplates = useViewCompiler(ProjectSharingChatterCompiler, arch, { Mail: template }, {});
        this.mailTemplate = mailTemplates.Mail;
        useExternalListener(window, "paste", this.onGlobalPaste, { capture: true });
        useExternalListener(window, "drop", this.onGlobalDrop, { capture: true });
    }

    get actionMenuItems() {
        return {};
    }

    get translateAlert() {
        return null;
    }

    onGlobalPaste(ev) {
        // prevent pasting an image on Description field as Portal users don't have access to ir.attachment
        ev.preventDefault();
        if (ev.target.closest('.o_field_widget[name="description"]')) {
            const items = ev.clipboardData.items;
            for (let i = 0; i < items.length; i++) {
                if (items[i].type.indexOf('image') !== -1) {
                    ev.stopImmediatePropagation();
                    return;
                }
            }
        }
    }

    onGlobalDrop(ev) {
        // prevent dropping an image on Description field as Portal users don't have access to ir.attachment
        ev.preventDefault();
        if (ev.target.closest('.o_field_widget[name="description"]')) {
            if(ev.dataTransfer.files.length > 0){
                ev.stopImmediatePropagation();
            }
        }
    }
}

ProjectSharingFormController.components = {
    ...FormController.components,
    ChatterContainer,
}
