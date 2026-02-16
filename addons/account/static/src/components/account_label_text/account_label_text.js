import { useRef } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { ListTextField } from "@web/views/fields/text/text_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { onMounted, onPatched } from "@odoo/owl";
import {
    ListSectionAndNoteText,
    listSectionAndNoteText,
    sectionAndNoteText,
} from "../section_and_note_fields_backend/section_and_note_fields_backend";

export class AccountLabelTextField extends ListTextField {
    static template = "account.AccountLabelTextField";
    static components = { Many2XAutocomplete };

    setup() {
        super.setup();
        this.rootRef = useRef("root");
        this.orm = useService("orm");
        this.action = useService("action");

        const fixM2xTabIndex = () => {
            const input = this.m2xInput;
            if (input) {
                input.tabIndex = -1;
            }
        };
        onMounted(fixM2xTabIndex);
        onPatched(fixM2xTabIndex);
    }

    getFirstLine(text) {
        return (text || "").split("\n")[0].trim();
    }

    get productId() {
        return this.props.record.data.product_id;
    }

    get productDomain() {
        const moveType = this.props.record.evalContext.parent?.move_type;
        if (["out_invoice", "out_refund", "out_receipt"].includes(moveType)) {
            return [["sale_ok", "=", true]];
        }
        return [["purchase_ok", "=", true]];
    }

    get m2xAutocompleteProps() {
        return {
            activeActions: { create: false, createEdit: false, write: false },
            autoSelect: true,
            fieldString: "Product",
            getDomain: () => this.productDomain,
            placeholder: "",
            resModel: "product.product",
            searchLimit: 8,
            update: async (records) => {
                const rec = records?.[0];
                if (!rec) {
                    return;
                }
                await this.props.record.update({ product_id: { id: rec.id } });
                // useInputField won't auto-sync when dirty (user was typing), force it.
                const textarea = this.textareaRef.el;
                if (textarea) {
                    textarea.value = this.props.record.data[this.props.name] || "";
                    textarea.focus();
                }
            },
            value: "",
        };
    }

    get m2xInput() {
        return this.rootRef.el?.querySelector(".o_m2o_overlay .o-autocomplete--input");
    }

    get isDropdownVisible() {
        const menu = this.rootRef.el?.querySelector(
            ".o_m2o_overlay .o-autocomplete--dropdown-menu"
        );
        if (!menu) {
            return false;
        }
        if (menu.querySelector(".o_loading") || menu.querySelector("li.o_m2o_no_result")) {
            return false;
        }
        return true;
    }

    async onLabelInput() {
        const textarea = this.textareaRef.el;
        if (!textarea) {
            return;
        }

        const firstNewline = textarea.value.indexOf("\n");
        if (firstNewline !== -1 && textarea.selectionStart > firstNewline) {
            return;
        }

        if (this.productId) {
            await this.props.record.update({ product_id: false });
        }

        const firstLine = this.getFirstLine(textarea.value);
        const m2xInput = this.m2xInput;
        if (!m2xInput) {
            return;
        }

        if (firstLine) {
            m2xInput.value = firstLine;
            m2xInput.dispatchEvent(new InputEvent("input", { bubbles: true }));
        } else if (this.isDropdownVisible) {
            m2xInput.dispatchEvent(
                new KeyboardEvent("keydown", { key: "Escape", bubbles: false, cancelable: true })
            );
        }
    }

    onLabelKeydown(ev) {
        if (!this.isDropdownVisible) {
            return;
        }
        const m2xInput = this.m2xInput;
        if (!m2xInput) {
            return;
        }

        const navKeys = ["ArrowUp", "ArrowDown", "Enter", "Escape", "Tab"];
        if (!navKeys.includes(ev.key)) {
            return;
        }

        // stopImmediatePropagation also blocks useInputField's onKeydown from running commitChanges concurrently.
        ev.stopImmediatePropagation();
        m2xInput.dispatchEvent(
            new KeyboardEvent("keydown", {
                key: ev.key,
                code: ev.code,
                bubbles: false,
                cancelable: true,
                shiftKey: ev.shiftKey,
                ctrlKey: ev.ctrlKey,
                metaKey: ev.metaKey,
            })
        );
        ev.preventDefault();
    }

    async onBlur() {
        super.onBlur();
        // Reset the autocomplete's inEdition flag so it doesn't carry stale state on next focus.
        this.m2xInput?.dispatchEvent(new FocusEvent("blur", { bubbles: false }));
    }

    async openProduct(newWindow = false) {
        if (!this.productId) {
            return;
        }
        const action = await this.orm.call("product.product", "get_formview_action", [
            [this.productId.id],
        ]);
        await this.action.doAction(action, { newWindow });
    }
}

export class AccountLabelSectionAndNoteText extends ListSectionAndNoteText {
    static template = "account.AccountLabelSectionAndNoteText";

    get componentToUse() {
        const record = this.props.record;
        if (record.data.display_type === "product" && "product_id" in record.activeFields) {
            return AccountLabelTextField;
        }
        return super.componentToUse;
    }
}

registry.category("fields").add("account_label_text", sectionAndNoteText);
registry.category("fields").add("list.account_label_text", {
    ...listSectionAndNoteText,
    component: AccountLabelSectionAndNoteText,
});
