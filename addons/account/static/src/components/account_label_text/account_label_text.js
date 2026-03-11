import { useState } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { usePosition } from "@web/core/position/position_hook";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { ListTextField } from "@web/views/fields/text/text_field";
import {
    ListSectionAndNoteText,
    listSectionAndNoteText,
    sectionAndNoteText,
} from "../section_and_note_fields_backend/section_and_note_fields_backend";


export class AccountLabelTextField extends ListTextField {
    static template = "account.AccountLabelTextField";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ suggestions: [], showDropdown: false });
        this.debouncedSearch = useDebounced(this.searchProducts.bind(this), 250);

        usePosition("dropdownList", () => this.textareaRef.el, {
            position: "bottom-start",
        });

    }

    getFirstLine(text) {
        return (text || "").split("\n")[0].trim();
    };

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

    async searchProducts(firstLine) {
        if (!firstLine) {
            this.state.suggestions = [];
            this.state.showDropdown = false;
            return;
        }
        const results = await this.orm.call("product.product", "name_search", [], {
            name: firstLine,
            domain: this.productDomain,
            limit: 8,
        });
        this.state.suggestions = results;
        this.state.showDropdown = results.length > 0;
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
        if (firstLine) {
            this.debouncedSearch(firstLine);
        } else {
            this.state.suggestions = [];
            this.state.showDropdown = false;
        }
    }

    async selectProduct(suggestion) {
        await this.props.record.update({ product_id: { id: suggestion[0] } });
        // Force-sync textarea: useInputField considers it dirty (user was typing)
        // so it won't pick up the value computed by the onchange automatically.
        const textarea = this.textareaRef.el;
        if (textarea) {
            textarea.value = this.props.record.data[this.props.name] || "";
        }
        this.state.showDropdown = false;
    }

    async openProduct() {
        if (!this.productId) {
            return;
        }
        const action = await this.orm.call("product.product", "get_formview_action", [
            [this.productId.id],
        ]);
        await this.action.doAction(action);
    }

    async onBlur() {
        super.onBlur();
        this.state.showDropdown = false;
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
