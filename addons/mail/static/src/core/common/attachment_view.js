import { propSignal } from "@mail/utils/common/hooks";

import { Component, onWillUnmount, signal, t, useOnChange } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { hidePDFJSButtons } from "@web/core/utils/pdfjs";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";

class AbstractAttachmentView extends Component {
    static template = "mail.AttachmentView";
    static components = {};

    iframeViewerPdfRef = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.thread = propSignal("thread", t.instanceOf(this.store["mail.thread"]));
        this.uiService = useService("ui");
        this.isMobileOS = isMobileOS();
        useOnChange(
            () => [this.iframeViewerPdfRef()],
            (el) => {
                if (el) {
                    hidePDFJSButtons(el);
                }
            }
        );
    }

    onClickNext() {
        const index = this.thread().attachmentsInWebClientView.findIndex((attachment) =>
            attachment.eq(this.thread().message_main_attachment_id)
        );
        this.thread().setMainAttachmentFromIndex(
            index >= this.thread().attachmentsInWebClientView.length - 1 ? 0 : index + 1
        );
    }

    onClickPrevious() {
        const index = this.thread().attachmentsInWebClientView.findIndex((attachment) =>
            attachment.eq(this.thread().message_main_attachment_id)
        );
        this.thread().setMainAttachmentFromIndex(
            index <= 0 ? this.thread().attachmentsInWebClientView.length - 1 : index - 1
        );
    }

    get displayName() {
        return this.thread().message_main_attachment_id.name;
    }

    get showsPopoutControl() {
        return !this.isMobileOS;
    }

    onClickPopout() {}
}

/*
 * AttachmentView inside popout window.
 * Popout features disabled as this only makes sense in the non-popout AttachmentView.
 */
export class PopoutAttachmentView extends AbstractAttachmentView {
    static template = "mail.PopoutAttachmentView";
}

/**
 * Signal for the popout's thread, passed straight to the popout component, which reads it
 * and re-renders in place when the thread changes.
 *
 * @param {Object} signals
 * @param {import("@odoo/owl").Signal<import("models").Thread>} signals.thread
 */
export function usePopoutAttachment({ thread }) {
    const uiService = useService("ui");
    const mailPopoutService = useService("mail.popout");
    const notification = useService("notification");

    function attachmentViewParentElementClassList() {
        const attachmentViewEl = document.querySelector(".o-mail-Attachment");
        let parentElementClassList;
        if ((parentElementClassList = attachmentViewEl?.parentElement?.classList)) {
            return parentElementClassList;
        }
        return null;
    }

    function showAttachmentView() {
        const parentElementClassList = attachmentViewParentElementClassList();
        const hiddenClass = "d-none";
        if (parentElementClassList?.contains(hiddenClass)) {
            parentElementClassList.remove(hiddenClass);
        }
    }

    function hideAttachmentView() {
        const parentElementClassList = attachmentViewParentElementClassList();
        const hiddenClass = "d-none";
        if (!parentElementClassList?.contains(hiddenClass)) {
            parentElementClassList?.add(hiddenClass);
        }
    }

    function popout() {
        if (isMobileOS()) {
            return notification.add(_t("Pop out is not supported on mobile."), { type: "warning" });
        }
        mailPopoutService.addHooks(
            () => {
                hideAttachmentView();
                uiService.bus.trigger("resize");
            },
            () => {
                showAttachmentView();
                uiService.bus.trigger("resize");
            }
        );
        mailPopoutService.popout(PopoutAttachmentView, { thread });
    }

    function resetPopout() {
        mailPopoutService.reset();
    }

    onWillUnmount(resetPopout);
    return { popout };
}

export class AttachmentView extends AbstractAttachmentView {
    setup() {
        super.setup();
        this.attachmentPopout = usePopoutAttachment({ thread: this.thread });
    }

    onClickPopout() {
        this.attachmentPopout.popout();
    }
}
