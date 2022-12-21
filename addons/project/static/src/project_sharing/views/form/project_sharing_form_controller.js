/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { createElement } from "@web/core/utils/xml";
import { FormController } from '@web/views/form/form_controller';
import { useViewCompiler } from '@web/views/view_compiler';
import { ProjectSharingChatterCompiler } from './project_sharing_form_compiler';
import { ChatterContainer } from '../../components/chatter/chatter_container';

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
    }

    get actionMenuItems() {
        return {};
    }

    get translateAlert() {
        return null;
    }
}

ProjectSharingFormController.components = {
    ...FormController.components,
    ChatterContainer,
}
