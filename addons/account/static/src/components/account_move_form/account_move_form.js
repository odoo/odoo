/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createElement, append } from "@web/core/utils/xml";
import { Notebook } from "@web/core/notebook/notebook";
import { formView } from "@web/views/form/form_view";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormController } from '@web/views/form/form_controller';
import { useService } from "@web/core/utils/hooks";

export class AccountMoveController extends FormController {
    setup() {
        super.setup();
        this.account_move_service = useService("account_move");
    }

    async deleteRecord() {
        if ( !await this.account_move_service.addDeletionDialog(this, this.model.root.resId)) {
            return super.deleteRecord(...arguments);
        }
    }
};

export class AccountMoveFormNotebook extends Notebook {
    static template = "account.AccountMoveFormNotebook";
    static props = {
        ...Notebook.props,
        onBeforeTabSwitch: { type: Function, optional: true },
    };

    async changeTabTo(page_id) {
        if (this.props.onBeforeTabSwitch) {
            await this.props.onBeforeTabSwitch(page_id);
        }
        this.state.currentPage = page_id;
    }
}

export class AccountMoveFormRenderer extends FormRenderer {
    static components = {
        ...FormRenderer.components,
        AccountMoveFormNotebook: AccountMoveFormNotebook,
    };

    async saveBeforeTabChange() {
        if (this.props.record.isInEdition && await this.props.record.isDirty()) {
            const contentEl = document.querySelector('.o_content');
            const scrollPos = contentEl.scrollTop;
            await this.props.record.save();
            if (scrollPos) {
                contentEl.scrollTop = scrollPos;
            }
        }
    }
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
    Controller: AccountMoveController,
};

registry.category("views").add("account_move_form", AccountMoveFormView);
