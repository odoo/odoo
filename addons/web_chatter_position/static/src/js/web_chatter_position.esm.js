/** @odoo-module **/
/*
    Copyright 2023 Camptocamp SA (https://www.camptocamp.com).
    License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
*/

import {FormCompiler} from "@web/views/form/form_compiler";
import {FormController} from "@web/views/form/form_controller";
import {MailFormCompiler} from "@mail/views/form/form_compiler";
import {append} from "@web/core/utils/xml";
import {patch} from "@web/core/utils/patch";

/**
 * So, you've landed here and you have no idea what this is about. Don't worry, you're
 * not the only one. Here's a quick summary of what's going on:
 *
 * In core, the chatter position depends on the size of the screen and wether there is
 * an attachment viewer or not. There are 3 possible positions, and for each position a
 * different chatter instance is displayed.
 *
 * So, in fact, we have 3 chatter instances running, and we switch their visibility
 * depending on the desired position.
 *
 * A) Bottom position
 *    https://github.com/odoo/odoo/blob/2ef010907/addons/mail/static/src/views/form/form_compiler.js#L160
 *    Condition: `!this.props.hasAttachmentViewer and uiService.size < ${SIZES.XXL}`
 *
 *    This is the bottom position you would except. However it can only be there until
 *    XXL screen sizes, because the container is a flexbox and changes from row to
 *    column display. It's hidden in the presence of an attachment viewer.
 *
 * B) Bottom In-sheet position
 *    https://github.com/odoo/odoo/blob/2ef010907/addons/mail/static/src/views/form/form_compiler.js#L181
 *    Condition: `this.props.hasAttachmentViewer`
 *
 *    This is the bottom position that's used when there's an attachment viewer in place.
 *    It's rendered within the form sheet, possibly to by-pass the flexbox issue
 *    beforementioned. It's only instanciated when there's an attachment viewer.
 *
 * C) Sided position
 *    https://github.com/odoo/odoo/blob/2ef010907/addons/mail/static/src/views/form/form_compiler.js#L83
 *    Condition: `!hasAttachmentViewer() and uiService.size >= ${SIZES.XXL}`
 *
 *    This is the sided position, hidden in the presence of an attachment viewer.
 *    It's the better half of `A`.
 *
 * The patches and overrides you see below are here to alter these conditions to force
 * a specific position regardless of the screen size, depending on an user setting.
 */

patch(MailFormCompiler.prototype, "web_chatter_position", {
    /**
     * Patch the visibility of the Sided chatter (`C` above).
     *
     * @override
     */
    compile() {
        const res = this._super.apply(this, arguments);
        const chatterContainerHookXml = res.querySelector(
            ".o_FormRenderer_chatterContainer"
        );
        if (!chatterContainerHookXml) {
            return res;
        }
        // Don't patch anything if the setting is "auto": this is the core behaviour
        if (odoo.web_chatter_position === "auto") {
            return res;
        } else if (odoo.web_chatter_position === "sided") {
            chatterContainerHookXml.setAttribute("t-if", "!hasAttachmentViewer()");
        } else if (odoo.web_chatter_position === "bottom") {
            chatterContainerHookXml.setAttribute("t-if", false);
        }
        return res;
    },
});

patch(FormCompiler.prototype, "web_chatter_position", {
    /**
     * Patch the css classes of the `Form`, to include an extra `h-100` class.
     * Without it, the form sheet will not be full height in some situations,
     * looking a bit weird.
     *
     * @override
     */
    compileForm() {
        const res = this._super.apply(this, arguments);
        if (odoo.web_chatter_position === "sided") {
            const classes = res.getAttribute("t-attf-class");
            res.setAttribute("t-attf-class", `${classes} h-100`);
        }
        return res;
    },
    /**
     * Patch the visibility of bottom chatters (`A` and `B` above).
     * `B` may not exist in some situations, so we ensure it does by creating it.
     *
     * @override
     */
    compile(node, params) {
        const res = this._super.apply(this, arguments);
        const chatterContainerHookXml = res.querySelector(
            ".o_FormRenderer_chatterContainer:not(.o-isInFormSheetBg)"
        );
        if (!chatterContainerHookXml) {
            return res;
        }
        if (chatterContainerHookXml.parentNode.classList.contains("o_form_sheet")) {
            return res;
        }
        // Don't patch anything if the setting is "auto": this is the core behaviour
        if (odoo.web_chatter_position === "auto") {
            return res;
            // For "sided", we have to remote the bottom chatter
            // (except if there is an attachment viewer, as we have to force bottom)
        } else if (odoo.web_chatter_position === "sided") {
            chatterContainerHookXml.setAttribute("t-if", false);
            // For "bottom", we keep the chatter in the form sheet
            // (the one used for the attachment viewer case)
            // If it's not there, we create it.
        } else if (odoo.web_chatter_position === "bottom") {
            if (params.hasAttachmentViewerInArch) {
                const sheetBgChatterContainerHookXml = res.querySelector(
                    ".o_FormRenderer_chatterContainer.o-isInFormSheetBg"
                );
                sheetBgChatterContainerHookXml.setAttribute("t-if", true);
                chatterContainerHookXml.setAttribute("t-if", false);
            } else {
                const formSheetBgXml = res.querySelector(".o_form_sheet_bg");
                const sheetBgChatterContainerHookXml =
                    chatterContainerHookXml.cloneNode(true);
                sheetBgChatterContainerHookXml.classList.add("o-isInFormSheetBg");
                sheetBgChatterContainerHookXml.setAttribute("t-if", true);
                append(formSheetBgXml, sheetBgChatterContainerHookXml);
                const sheetBgChatterContainerXml =
                    sheetBgChatterContainerHookXml.querySelector("ChatterContainer");
                sheetBgChatterContainerXml.setAttribute("isInFormSheetBg", "true");
                chatterContainerHookXml.setAttribute("t-if", false);
            }
        }
        return res;
    },
});

patch(FormController.prototype, "web_chatter_position", {
    /**
     * Patch the css classes of the form container, to include an extra `flex-row` class.
     * Without it, it'd go for flex columns direction and it won't look good.
     *
     * @override
     */
    get className() {
        const result = this._super();
        if (odoo.web_chatter_position === "sided") {
            result["flex-row"] = true;
        }
        return result;
    },
});
