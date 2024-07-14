/** @odoo-module */

import { isComponentNode } from "@web/views/view_compiler";
import {
    computeXpath,
    applyInvisible,
} from "@web_studio/client_action/view_editor/editors/xml_utils";
import { createElement } from "@web/core/utils/xml";
import { formView } from "@web/views/form/form_view";
import { objectToString } from "@web/views/form/form_compiler";

const interestingSelector = [
    ":not(field) sheet", // A hook should be present to add elements in the sheet
    ":not(field) field", // should be clickable and draggable
    ":not(field) notebook", // should be able to add pages
    ":not(field) page", // should be clickable
    ":not(field) button", // should be clickable
    ":not(field) label", // should be clickable
    ":not(field) group", // any group: outer or inner
    ":not(field) group group > *", // content of inner groups serves as main dropzone
    ":not(field) div.oe_chatter",
    ":not(field) .oe_avatar",
].join(", ");

export class FormEditorCompiler extends formView.Compiler {
    compile(key, params = {}) {
        const xml = this.templates[key];

        // One pass to compute and add the xpath for the arch's node location
        // onto that node.
        for (const el of xml.querySelectorAll(interestingSelector)) {
            const xpath = computeXpath(el);
            el.setAttribute("studioXpath", xpath);
        }

        // done after construction of xpaths
        this.addChatter = true;
        this.chatterData = {
            remove_message_ids: false,
            remove_follower_ids: false,
            remove_activity_ids: false,
        };
        this.avatars = [];

        const compiled = super.compile(key, params);

        const sheetBg = compiled.querySelector(".o_form_sheet_bg");
        if (sheetBg) {
            const studioHook = createElement("StudioHook", {
                xpath: `"${sheetBg.getAttribute("studioXpath")}"`,
                position: "'inside'",
                type: "'insideSheet'",
            });
            sheetBg.querySelector(".o_form_sheet").prepend(studioHook);
        }

        if (this.addChatter) {
            const chatterContainerHook = createElement("ChatterContainerHook", {
                threadModel: `__comp__.props.record.resModel`,
                chatterData: objectToString(this.chatterData),
            });
            const el = compiled.querySelector(".o_form_sheet") || compiled;
            el.after(chatterContainerHook);
        } else {
            const parent = compiled.querySelector(".o-mail-Form-chatter");
            parent.removeAttribute("t-attf-class"); // avoid class o-aside
            parent.removeAttribute("t-if");
        }

        const checkStatusBarButtons = compiled.querySelector("StatusBarButtons");
        if(!checkStatusBarButtons) {
            const addButtonAction = createElement("AddButtonAction");     
            const el = compiled.querySelector(".o_form_sheet_bg") || compiled;
            el.prepend(addButtonAction);
        }

        const fieldStatus = compiled.querySelector(`Field[type="'statusbar'"]`); // change selector at some point
        if (!fieldStatus) {
            const addStatusBar = !compiled.querySelector(".o_form_statusbar");
            const statusBarFieldHook = createElement("StatusBarFieldHook", { addStatusBar });
            const el = compiled.querySelector(".o_form_sheet_bg") || compiled;
            el.prepend(statusBarFieldHook);
        }

        // the button box is included in the control panel, which is not visible in Studio
        // re-add it to the form view
        const buttonBoxXml = xml.querySelector("div[name='button_box']:not(field div)");
        let buttonBox;
        const buttonBoxContainer = createElement("div", {
            class: "d-flex justify-content-end my-2",
        });
        if (buttonBoxXml) {
            buttonBox = this.compileNode(buttonBoxXml, params);
        } else {
            buttonBox = createElement("ButtonBox");
        }
        buttonBoxContainer.append(buttonBox);
        const el = compiled.querySelector(".o_form_sheet_bg") || compiled;
        el.prepend(buttonBoxContainer);

        const buttonHook = createElement(
            "t",
            [createElement("ButtonHook", { add_buttonbox: !buttonBoxXml })],
            { "t-set-slot": `slot_button_hook` }
        );

        buttonBox.insertAdjacentElement("afterbegin", buttonHook);

        // Note: the ribon does not allow to remove an existing avatar!
        const title = compiled.querySelector(".oe_title");
        if (title) {
            if (
                !title.querySelector(":scope > h1 > [isAvatar]") && // check it works with <field class="oe_avatar" ... />
                !title.parentElement.querySelector(":scope > [isAvatar]")
            ) {
                const avatarHook = createElement("AvatarHook", {
                    fields: `__comp__.props.record.fields`,
                });
                avatarHook.setAttribute(
                    "class",
                    `'oe_avatar d-flex align-items-center justify-content-center ms-3 o_web_studio_avatar h4'`
                );
                title.before(avatarHook);
            }
        }
        for (const el of this.avatars) {
            el.removeAttribute("isAvatar");
        }

        compiled.querySelectorAll(":not(.o_form_statusbar) Field").forEach((el) => {
            el.setAttribute("hasEmptyPlaceholder", "true");
        });

        compiled
            .querySelectorAll(`InnerGroup > t[t-set-slot][subType="'item_component'"] Field`)
            .forEach((el) => {
                el.setAttribute("hasLabel", "true");
            });

        return compiled;
    }

    applyInvisible(invisible, compiled, params) {
        return applyInvisible(invisible, compiled, params);
    }

    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        const studioXpath = label.getAttribute("studioXpath");
        const formLabel = super.createLabelFromField(...arguments);
        formLabel.setAttribute("studioXpath", `"${studioXpath}"`);
        if (formLabel.hasAttribute("t-if")) {
            formLabel.setAttribute("studioIsVisible", formLabel.getAttribute("t-if"));
            formLabel.removeAttribute("t-if");
        }
        return formLabel;
    }

    compileNode(node, params = {}, evalInvisible = true) {
        const nodeType = node.nodeType;
        // Put a xpath on the currentSlot containing the future compiled element.
        // Do it early not to be bothered by recursive call to compileNode.
        const currentSlot = params.currentSlot;
        if (nodeType === 1 && currentSlot && !currentSlot.hasAttribute("studioXpath")) {
            const parentElement = node.parentElement;
            if (parentElement && parentElement.tagName === "page") {
                const xpath = computeXpath(node.parentElement);
                currentSlot.setAttribute("studioXpath", `"${xpath}"`);
                // If the page has an OuterGroup as last child, don't add a page studioHook
                if (!parentElement.querySelector(":scope > group:last-child > group")) {
                    const pageHookProps = {
                        position: "'inside'",
                        type: "'page'",
                        xpath: `"${xpath}"`,
                    };
                    currentSlot.setAttribute("studioHookProps", objectToString(pageHookProps));
                }
            } else {
                const xpath = node.getAttribute("studioXpath");
                currentSlot.setAttribute("studioXpath", `"${xpath}"`);
            }
        }

        if (nodeType === 1 && node.getAttribute("studio_no_fetch")) {
            return;
        }

        const compiled = super.compileNode(node, { ...params, compileInvisibleNodes: true }, true); // always evalInvisible

        if (nodeType === 1) {
            // Put a xpath on anything of interest.
            if (node.hasAttribute("studioXpath")) {
                const xpath = node.getAttribute("studioXpath");
                if (isComponentNode(compiled)) {
                    compiled.setAttribute("studioXpath", `"${xpath}"`);
                } else if (!compiled.hasAttribute("studioXpath")) {
                    compiled.setAttribute("studioXpath", xpath);
                }
            }

            if (node.tagName === "notebook") {
                // Since empty pages are not compiled, this compiler has not applied the studioXpath attribute.
                // We must need to add one as well as the other pages, to make sure we can edit its content properly.
                const originalChildren = Array.from(node.children).filter(
                    (e) => e.tagName === "page"
                );
                Array.from(compiled.children).forEach((elem, index) => {
                    if (!elem.hasAttribute("studioXpath")) {
                        const studioXpath = originalChildren[index].getAttribute("studioXpath");
                        elem.setAttribute("studioXpath", `"${studioXpath}"`);
                        const pageHookProps = {
                            position: "'inside'",
                            type: "'page'",
                            xpath: `"${studioXpath}"`,
                        };
                        elem.setAttribute("studioHookProps", objectToString(pageHookProps));
                    }
                });
            }

            if (node.classList.contains("oe_chatter")) {
                this.addChatter = false;
                const chatterNode = compiled.querySelector(
                    "t[t-component='__comp__.mailComponents.Chatter']"
                );
                const xpath = node.getAttribute("studioXpath");
                chatterNode.setAttribute("studioXpath", `"${xpath}"`);
                compiled.setAttribute("data-studio-xpath", xpath);
                compiled.classList.add("o-web-studio-editor--element-clickable");
            }
            if (node.classList.contains("oe_avatar")) {
                compiled.setAttribute("isAvatar", true);
                this.avatars.push(compiled);
            }
            const name = node.getAttribute("name"); // not sure that part works
            if (name === "message_ids") {
                this.chatterData.remove_message_ids = true;
            } else if (name === "message_follower_ids") {
                this.chatterData.remove_follower_ids = true;
            } else if (name === "activity_ids") {
                this.chatterData.remove_activity_ids = true;
            }
        }
        return compiled;
    }
}
