/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { closestBlock, setCursorEnd } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { patch } from "@web/core/utils/patch";
import { MentionList } from "@mail/core/web/mention_list";
import { url } from "@web/core/utils/urls";
import { usePopover } from "@web/core/popover/popover_hook";
import { isEventHandled } from "@web/core/utils/misc";

patch(Wysiwyg.prototype, {
    setup() {
        super.setup();
        if (this.inDiscuss) {
            this.mentionList = usePopover(MentionList, {
                position: `bottom-start`,
                onClose: () => this.focus(),
            });
            this.triggerMentionList = this.triggerMentionList.bind(this);
        }
    },
    get inDiscuss() {
        return this.props.options.recordInfo?.res_model === "mail.compose.message";
    },
    async startEdition() {
        const res = await super.startEdition(...arguments);
        // Only enable mention list in full chatter mode web editor
        if (this.inDiscuss) {
            this.odooEditor.document.addEventListener("keydown", this.triggerMentionList, true);
            this.odooEditor.document.addEventListener("click", this.triggerMentionList, true);
        }
        return res;
    },
    destroy() {
        super.destroy();
        if (this.inDiscuss && this.odooEditor) {
            this.odooEditor.document.removeEventListener("keydown", this.triggerMentionList, true);
            this.odooEditor.document.removeEventListener("click", this.triggerMentionList, true);
        }
    },
    async triggerMentionList(ev) {
        if (!this.inDiscuss) {
            return;
        }
        // Let event be handled by bubbling handlers and other handlers from Odoo Editor first.
        await new Promise((resolve) => setTimeout(resolve, 0));
        const selection = this.odooEditor.document.getSelection();
        if (
            this.isSelectionInEditable() &&
            selection.isCollapsed &&
            selection.rangeCount &&
            !this.mentionList.isOpen &&
            (ev.key === "@" || ev.key === "#")
        ) {
            this.stepBeforeMention = this.odooEditor._historySteps.length - 2;
            const closest = closestBlock(this.odooEditor.document.getSelection().anchorNode);
            this.mentionList.open(closest, {
                type: ev.key === "@" ? "partner" : "channel",
                onSelect: this.selectMention.bind(this),
            });
        } else if (!isEventHandled(ev, "MentionList.onKeydown")) {
            this.mentionList.close();
        }
    },
    selectMention(ev, option) {
        if (!this.inDiscuss) {
            return;
        }
        this.mentionList.close();
        const mentionBlock = renderToElement("mail.Wysiwyg.mentionLink", {
            option,
            href: `${url("/web")}#model=${option.partner ? "res.partner" : "discuss.channel"}&id=${
                option.partner ? option.partner.id : option.channel.id
            }`,
        });
        const nameNode = document.createTextNode(`${option.partner ? "@" : "#"}${option.label}`);
        const space = document.createTextNode("\u00A0");
        mentionBlock.appendChild(nameNode);
        this.odooEditor.historyRevertUntil(this.stepBeforeMention);
        this.odooEditor.execCommand("insert", mentionBlock);
        this.odooEditor.execCommand("insert", space);
        setCursorEnd(space, false);
        this.odooEditor.historyStep();
    },
});
