/** @odoo-module native */
import { useRef } from "@odoo/owl";
import { Notebook } from "@web/components/notebook";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { append, createElement } from "@web/core/utils/dom/xml";
import { useService } from "@web/core/utils/hooks";
import { deleteConfirmationMessage } from "@web/ui/dialog";
import { FormCompiler, FormController, FormRenderer, formView } from "@web/views/form";

const log = makeLogger("account.move.form");

export class AccountMoveFormController extends FormController {
    setup() {
        super.setup();
        this.account_move_service = useService("account_move");
    }

    get cogMenuProps() {
        return {
            ...super.cogMenuProps,
            printDropdownTitle: _t("Print"),
            loadExtraPrintItems: this.loadExtraPrintItems.bind(this),
        };
    }

    async loadExtraPrintItems() {
        const items = await this.orm.call("account.move", "get_extra_print_items", [
            this.model.root.resId,
        ]);
        return items.filter((item) => item.key !== "download_all");
    }

    async deleteRecord() {
        log.logic("deleteRecord", () => ({
            resId: this.model.root.resId,
            moveType: this.model.root.data.move_type,
        }));
        const deleteConfirmationDialogProps = this.deleteConfirmationDialogProps;
        deleteConfirmationDialogProps.body =
            await this.account_move_service.getDeletionDialogBody(
                deleteConfirmationMessage,
                this.model.root.resId,
            );
        this.deleteRecordsWithConfirmation(deleteConfirmationDialogProps, [
            this.model.root,
        ]);
    }
}

export class AccountMoveFormNotebook extends Notebook {
    static template = "account.AccountMoveFormNotebook";
    static props = {
        ...Notebook.props,
        onBeforeTabSwitch: { type: Function, optional: true },
    };

    async beforePageActivation(pageId) {
        if ((await super.beforePageActivation(pageId)) === false) {
            return false;
        }
        return this.props.onBeforeTabSwitch?.(pageId);
    }
}

export class AccountMoveFormRenderer extends FormRenderer {
    static components = {
        ...FormRenderer.components,
        AccountMoveFormNotebook: AccountMoveFormNotebook,
    };

    setup() {
        super.setup();
        this.rootRef = useRef("compiled_view_root");
    }

    async saveBeforeTabChange() {
        if (!this.props.record.isInEdition || !(await this.props.record.isDirty())) {
            return;
        }
        const contentEl = this.rootRef.el?.closest(".o_content");
        const scrollPos = contentEl?.scrollTop;
        const saved = await this.props.record.save();
        if (scrollPos) {
            contentEl.scrollTop = scrollPos;
        }
        return saved;
    }
}

export class AccountMoveFormCompiler extends FormCompiler {
    compileNotebook(el, params) {
        const originalNoteBook = super.compileNotebook(...arguments);
        const noteBook = createElement("AccountMoveFormNotebook");
        for (const attr of originalNoteBook.attributes) {
            noteBook.setAttribute(attr.name, attr.value);
        }
        noteBook.setAttribute(
            "onBeforeTabSwitch",
            "() => __comp__.saveBeforeTabChange()",
        );
        const slots = originalNoteBook.childNodes;
        append(noteBook, [...slots]);
        return noteBook;
    }
}

export const AccountMoveFormView = {
    ...formView,
    Renderer: AccountMoveFormRenderer,
    Compiler: AccountMoveFormCompiler,
    Controller: AccountMoveFormController,
};

registry.category("views").add("account_move_form", AccountMoveFormView);
