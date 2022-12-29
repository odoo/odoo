/* @odoo-module */

import { evaluateExpr } from "@web/core/py_js/py";
import { useService } from "@web/core/utils/hooks";
import { SIZES } from "@web/core/ui/ui_service";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { Chatter } from "./chatter";
import { useChildSubEnv } from "@odoo/owl";
import { FormCompiler } from "@web/views/form/form_compiler";

FormController.components.Chatter = Chatter;
FormRenderer.components.Chatter = Chatter;

patch(FormController.prototype, "mail/new", {
    setup() {
        const archXml = this.props.archInfo.xmlDoc;
        const xmlDocChatter = archXml.querySelector("div.oe_chatter");
        this.hasChatter = Boolean(xmlDocChatter);
        this.hasActivity =
            this.hasChatter && Boolean(xmlDocChatter.querySelector("field[name='activity_ids']"));
        this.hasFollowers =
            this.hasChatter &&
            Boolean(xmlDocChatter.querySelector("field[name='message_follower_ids']"));
        this.isAttachmentBoxOpenedInitially =
            this.hasChatter && this._isAttachmentBoxOpenedInitially(xmlDocChatter);
        if (xmlDocChatter) {
            const doc = archXml.ownerDocument;
            const rootT = doc.createElement("t");
            rootT.setAttribute("chatter", "");
            rootT.setAttribute("t-if", "__comp__.env.hasChatter()");
            const chatterTag = doc.createElement("Chatter");
            chatterTag.setAttribute("resId", "__comp__.props.record.resId");
            chatterTag.setAttribute("resModel", "__comp__.props.record.resModel");
            chatterTag.setAttribute("displayName", "__comp__.props.record.data.display_name");
            chatterTag.setAttribute("hasActivity", this.hasActivity);
            chatterTag.setAttribute("hasFollowers", this.hasFollowers);
            chatterTag.setAttribute(
                "isAttachmentBoxOpenedInitially",
                this.isAttachmentBoxOpenedInitially
            );
            chatterTag.setAttribute("webRecord", "__comp__.props.record.model.root");
            rootT.appendChild(chatterTag);
            xmlDocChatter.replaceWith(rootT);
        }
        useChildSubEnv({ hasChatter: () => !this.hasSideChatter() });
        this.uiService = useService("ui");

        this._super();
    },

    hasSideChatter() {
        return this.hasChatter && this.uiService.size >= SIZES.XXL;
    },

    _isAttachmentBoxOpenedInitially(xmlDocChatter) {
        const messageField = xmlDocChatter.querySelector("field[name='message_ids']");
        const messageFollowerField = xmlDocChatter.querySelector(
            "field[name='message_follower_ids']"
        );
        const messageOptions = evaluateExpr(
            (messageField && messageField.getAttribute("options")) || "{}"
        );
        const messageFollowerOptions = evaluateExpr(
            (messageFollowerField && messageFollowerField.getAttribute("options")) || "{}"
        );
        return Boolean(
            messageOptions["open_attachments"] || messageFollowerOptions["open_attachments"]
        );
    },
});

patch(FormCompiler.prototype, "mail/new", {
    compileGenericNode(el, params) {
        if (el.hasAttribute("chatter")) {
            return el;
        }
        return this._super(el, params);
    },
    validateNode(node) {
        if (!node.hasAttribute("chatter")) {
            return this._super(node);
        }
    },
});
