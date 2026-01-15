import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

export class AccountMoveStatusBarSecuredField extends StatusBarField {
    static template = "account.MoveStatusBarSecuredField";

    get isSecured() {
        return this.props.record.data['secured'];
    }

    get currentItem() {
        return this.getAllItems().find((item) => item.isSelected);
    }
}

export const accountMoveStatusBarSecuredField = {
    ...statusBarField,
    component: AccountMoveStatusBarSecuredField,
    displayName: _t("Status with secured indicator for Journal Entries"),
    supportedTypes: ["selection"],
    additionalClasses: ["o_field_statusbar"],
};

registry.category("fields").add("account_move_statusbar_secured", accountMoveStatusBarSecuredField);
