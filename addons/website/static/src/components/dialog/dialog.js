import { Dialog, dialogProps } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";
import { Component, props, proxy, t } from "@odoo/owl";

const NO_OP = () => {};

export class WebsiteDialog extends Component {
    static template = "website.WebsiteDialog";
    static components = { Dialog };
    props = props({
        ...dialogProps,
        title: t.string().optional(_t("Confirmation")),
        size: t.selection(["sm", "md", "lg", "xl", "fs", "fullscreen"]).optional("md"),
        primaryTitle: t.string().optional(_t("Ok")),
        primaryClick: t.function().optional(),
        secondaryTitle: t.string().optional(_t("Discard")),
        secondaryClick: t.function().optional(),
        showSecondaryButton: t.boolean().optional(true),
        close: t.function().optional(() => NO_OP),
        closeOnClick: t.boolean().optional(true),
        body: t.string().optional(),
        slots: t.object().optional(),
        showFooter: t.boolean().optional(true),
    });

    setup() {
        this.state = proxy({
            disabled: false,
        });
        this.modalRef = useChildRef();
    }
    /**
     * Disables the buttons of the dialog when a click is made.
     * If a handler is provided, await for its call.
     * If the prop closeOnClick is true, close the dialog.
     * Otherwise, restore the button.
     *
     * @param handler {function|void} The handler to protect.
     * @returns {function(): Promise} handler called when a click is made.
     */
    protectedClick(handler) {
        return async () => {
            if (this.state.disabled) {
                return;
            }
            this.state.disabled = true;
            if (handler) {
                await handler();
            }
            if (this.props.closeOnClick) {
                return this.props.close();
            }
            this.state.disabled = false;
        };
    }

    get contentClasses() {
        const websiteDialogClass = "o_website_dialog";
        if (this.props.contentClass) {
            return `${websiteDialogClass} ${this.props.contentClass}`;
        }
        return websiteDialogClass;
    }
}
