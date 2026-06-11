import { useOnChange } from "@mail/utils/common/hooks";
import { Component, computed, onWillUnmount, props, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { hidePDFJSButtons } from "@web/core/utils/pdfjs";
import { useLayoutEffect, useRef } from "@web/owl2/utils";

class AbstractAttachmentView extends Component {
    static template = "mail.AttachmentView";

    setup() {
        super.setup();
        this.props = props({
            threadId: t.signal(t.number()),
            threadModel: t.signal(t.string()),
        });
        this.store = useService("mail.store");
        this.uiService = useService("ui");
        this.iframeViewerPdfRef = useRef("iframeViewerPdf");
        this.thread = computed(() =>
            this.store["mail.thread"].insert({
                id: this.props.threadId(),
                model: this.props.threadModel(),
            })
        );
        useLayoutEffect(
            (el) => {
                if (el) {
                    hidePDFJSButtons(this.iframeViewerPdfRef.el);
                }
            },
            () => [this.iframeViewerPdfRef.el]
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

    onClickPopout() {}
}

/*
 * AttachmentView inside popout window.
 * Popout features disabled as this only makes sense in the non-popout AttachmentView.
 */
export class PopoutAttachmentView extends AbstractAttachmentView {
    static template = "mail.PopoutAttachmentView";
}

export function usePopoutAttachment(threadId, threadModel) {
    const uiService = useService("ui");
    const mailPopoutService = useService("mail.popout");

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
        mailPopoutService.popout(PopoutAttachmentView, {
            threadId,
            threadModel,
        });
    }

    function resetPopout() {
        mailPopoutService.reset();
    }

    useOnChange(
        () => [threadId, threadModel],
        (threadId, threadModel) => {
            if (mailPopoutService.externalWindow) {
                hideAttachmentView();
                mailPopoutService.popout(PopoutAttachmentView, {
                    threadId,
                    threadModel,
                });
            }
        }
    );
    onWillUnmount(resetPopout);
    return {
        popout,
        resetPopout,
    };
}

export class AttachmentView extends AbstractAttachmentView {
    setup() {
        super.setup();
        const threadId = computed(() => this.props.threadId);
        const threadModel = computed(() => this.props.threadModel);
        this.attachmentPopout = usePopoutAttachment(threadId, threadModel);
    }

    onClickPopout() {
        this.attachmentPopout.popout();
    }
}
