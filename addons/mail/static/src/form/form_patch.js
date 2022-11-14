/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { SIZES } from "@web/core/ui/ui_service";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { Chatter } from "./chatter";
import { useChildSubEnv } from "@odoo/owl";

FormController.components.Chatter = Chatter;
FormRenderer.components.Chatter = Chatter;

patch(FormController.prototype, "mail", {
    setup() {
        const archXml = this.props.archInfo.xmlDoc;
        const xmlDocChatter = archXml.querySelector("div.oe_chatter");
        if (xmlDocChatter) {
            const doc = archXml.ownerDocument;
            const rootT = doc.createElement("t");
            rootT.setAttribute("t-if", "env.hasChatter()");
            const chatterTag = doc.createElement("Chatter");
            chatterTag.setAttribute("resId", "props.record.resId");
            chatterTag.setAttribute("resModel", "props.record.resModel");
            chatterTag.setAttribute("displayName", "props.record.data.display_name");
            rootT.appendChild(chatterTag);
            xmlDocChatter.replaceWith(rootT);
        }
        this.hasChatter = Boolean(xmlDocChatter);
        useChildSubEnv({ hasChatter: () => !this.hasSideChatter() });
        this.uiService = useService("ui");

        this._super();
    },

    hasSideChatter() {
        return this.hasChatter && this.uiService.size >= SIZES.XXL;
    },
});
