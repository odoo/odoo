/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createElement, append } from "@web/core/utils/xml";
import { Notebook } from "@web/core/notebook/notebook";
import { formView } from "@web/views/form/form_view";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";

export class AccountMoveFormNotebook extends Notebook {
    async changeTabTo(page_id) {
        if (this.props.onBeforeTabSwitch) {
            await this.props.onBeforeTabSwitch(page_id);
        }
        this.state.currentPage = page_id;
    }
}
AccountMoveFormNotebook.template = "account.AccountMoveFormNotebook";
AccountMoveFormNotebook.props = {
    ...Notebook.props,
    onBeforeTabSwitch: { type: Function, optional: true },
}
export class AccountMoveFormRenderer extends FormRenderer {
    async saveBeforeTabChange() {
        if (this.props.record.mode === "edit" && this.props.record.isDirty) {
            const contentEl = document.querySelector('.o_content');
            const scrollPos = contentEl.scrollTop;
            await this.props.record.save({
                stayInEdition: true,
            });
            if (scrollPos) {
                contentEl.scrollTop = scrollPos;
            }
        }
    }
}
AccountMoveFormRenderer.components = {
    ...FormRenderer.components,
    AccountMoveFormNotebook: AccountMoveFormNotebook,
}
export class AccountMoveFormCompiler extends FormCompiler {
    compileNotebook(el, params) {
        const originalNoteBook = super.compileNotebook(...arguments);
        const noteBook = createElement("AccountMoveFormNotebook");
        for (const attr of originalNoteBook.attributes) {
            noteBook.setAttribute(attr.name, attr.value);
        }
        noteBook.setAttribute("onBeforeTabSwitch", "() => __comp__.saveBeforeTabChange()");
        const slots = originalNoteBook.childNodes;
        append(noteBook, [...slots]);
        return noteBook;
    }
}

export const AccountMoveFormView = {
    ...formView,
    Renderer: AccountMoveFormRenderer,
    Compiler: AccountMoveFormCompiler,
};

registry.category("views").add("account_move_form", AccountMoveFormView);
