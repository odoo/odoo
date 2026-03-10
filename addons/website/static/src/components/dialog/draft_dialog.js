import { Component, proxy, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

function getSkipDialogKey(isPublishing, pageOnly) {
    const action = isPublishing ? "publish" : "delete";
    const target = pageOnly ? "page" : "website";
    return `website_no_${action}_${target}_draft_dialog`;
}

/**
 * Asks the user to confirm a draft publish/delete, unless they opted out.
 *
 * @returns {Promise<boolean>} whether the action is confirmed
 */
export function confirmDraftAction(dialog, isPublishing, pageOnly) {
    if (localStorage.getItem(getSkipDialogKey(isPublishing, pageOnly))) {
        return Promise.resolve(true);
    }
    return new Promise((resolve) => {
        dialog.add(
            DraftActionDialog,
            { isPublishing, pageOnly, confirm: () => resolve(true) },
            { onClose: () => resolve(false) }
        );
    });
}

export class DraftActionDialog extends Component {
    static components = { CheckBox, Dialog };
    static template = "website_builder.DraftDialog";
    props = useProps({
        pageOnly: Boolean,
        isPublishing: Boolean,
        confirm: Function,
        close: Function,
    });

    setup() {
        this.state = proxy({ shouldShowAgain: true });
        this.title = _t("Confirmation");
        const action = this.props.isPublishing ? "publish" : "delete";
        const target = this.props.pageOnly ? "page" : "website";
        let body = `You are about to ${action} this ${target}'s draft.`;
        if (this.props.pageOnly) {
            body += ` If you've made changes to the shared components (header, footer, etc), or to the styles, it will ${action} it too.`;
        }
        this.body = _t(body);
    }

    toggleShouldShowAgain() {
        this.state.shouldShowAgain = !this.state.shouldShowAgain;
    }

    onConfirmClick() {
        if (!this.state.shouldShowAgain) {
            const localStorageKey = getSkipDialogKey(this.props.isPublishing, this.props.pageOnly);
            localStorage.setItem(localStorageKey, true);
        }
        this.props.confirm();
        this.props.close();
    }
}
