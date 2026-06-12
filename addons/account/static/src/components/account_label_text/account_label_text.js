import { onMounted, onPatched, props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { useDebounced } from "@web/core/utils/timing";
import { useRef } from "@web/owl2/utils";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { ListTextField, textFieldProps } from "@web/views/fields/text/text_field";
import {
    ListSectionAndNoteText,
    listSectionAndNoteText,
    sectionAndNoteText,
} from "../section_and_note_fields_backend/section_and_note_fields_backend";

export class AccountLabelTextField extends ListTextField {
    static template = "account.AccountLabelTextField";
    static components = { Many2XAutocomplete };
    props = props({
        ...textFieldProps,
        rowCount: t.number().optional(1),
        context: t.object().optional(),
        options: t.object().optional({}),
    });

    setup() {
        super.setup();
        this.rootRef = useRef("root");
        this.orm = useService("orm");
        this.action = useService("action");
        this.debouncedOnLabelInput = useDebounced(this.onLabelInput, 200);

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

    get product() {
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
            activeActions: { create: true, createEdit: false, write: false },
            autoSelect: true,
            fieldString: "Product",
            getDomain: () => this.productDomain,
            placeholder: "",
            resModel: this.m2XAutoCompleteModel,
            searchLimit: 8,
            update: (records) => this.onMany2XUpdate(records),
            value: "",
            context: this.props.context,
        };
    }

    get m2XAutoCompleteModel() {
        return "product.product";
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

    get canEditProduct() {
        return true;
    }

    async onMany2XUpdate(records) {
        const rec = records?.[0];
        if (!rec) {
            return;
        }
        await this.updateMany2XProduct(rec);
        // useInputField won't auto-sync when dirty (user was typing), force it.
        const textarea = this.textareaRef.el;
        if (textarea) {
            textarea.value = this.props.record.data[this.props.name] || "";
            textarea.focus();
        }
    }

    async updateMany2XProduct(record) {
        await this.props.record.update({ product_id: { id: record.id } });
    }

    async onLabelInput() {
        const textarea = this.textareaRef.el;
        if (!textarea || !this.canEditProduct) {
            return;
        }

        const firstNewline = textarea.value.indexOf("\n");
        if (firstNewline !== -1 && textarea.selectionStart > firstNewline) {
            return;
        }

        if (this.product) {
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
        if (!this.product) {
            return;
        }
        const action = await this.orm.call(this.m2XAutoCompleteModel, "get_record_default_action", [
            [this.product.id],
        ]);
        await this.action.doAction(action, { newWindow });
    }
}

export class AccountLabelSectionAndNoteText extends ListSectionAndNoteText {
    static template = "account.AccountLabelSectionAndNoteText";
    props = props({
        ...standardFieldProps,
        context: t.object().optional(),
        options: t.object().optional({}),
    });

    get componentToUse() {
        const record = this.props.record;
        if (record.data.display_type === "product" && "product_id" in record.activeFields) {
            return AccountLabelTextField;
        }
        return super.componentToUse;
    }

    get componentProps() {
        if (this.componentToUse === AccountLabelTextField) {
            return this.props;
        }
        return omit(this.props, "context");
    }
}

export const listAccountLabelSectionAndNoteText = {
    ...listSectionAndNoteText,
    component: AccountLabelSectionAndNoteText,
    extractProps: (_staticInfo, dynamicInfo) => ({
        context: dynamicInfo.context,
    }),
};

registry.category("fields").add("account_label_text", sectionAndNoteText);
registry.category("fields").add("list.account_label_text", listAccountLabelSectionAndNoteText);
