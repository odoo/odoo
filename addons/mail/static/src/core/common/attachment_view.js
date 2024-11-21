import {
    Component,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    useComponent,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { deepEqual } from "@web/core/utils/objects";
import { hidePDFJSButtons } from "@web/libs/pdfjs";

class AbstractAttachmentView extends Component {
    static template = "mail.AttachmentView";
    static components = {};
    static props = ["threadId", "threadModel"];

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.uiService = useService("ui");
        this.iframeViewerPdfRef = useRef("iframeViewerPdf");
        this.state = useState({
            /** @type {import("models").Thread|undefined} */
            thread: undefined,
        });
        useEffect(() => {
            if (this.iframeViewerPdfRef.el) {
                hidePDFJSButtons(this.iframeViewerPdfRef.el);
            }
        });
        this.updateFromProps(this.props);
        onWillUpdateProps((props) => this.updateFromProps(props));
    }

    onClickNext() {
        const index = this.state.thread.attachmentsInWebClientView.findIndex((attachment) =>
            attachment.eq(this.state.thread.mainAttachment)
        );
        this.state.thread.setMainAttachmentFromIndex(
            index === this.state.thread.attachmentsInWebClientView.length - 1 ? 0 : index + 1
        );
    }

    onClickPrevious() {
        const index = this.state.thread.attachmentsInWebClientView.findIndex((attachment) =>
            attachment.eq(this.state.thread.mainAttachment)
        );
        this.state.thread.setMainAttachmentFromIndex(
            index === 0 ? this.state.thread.attachmentsInWebClientView.length - 1 : index - 1
        );
    }

    updateFromProps(props) {
        this.state.thread = this.store.Thread.insert({
            id: props.threadId,
            model: props.threadModel,
        });
    }

    get displayName() {
        return this.state.thread.mainAttachment.filename;
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

export function usePopoutAttachment() {
    const component = useComponent();
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

    function extractPopoutProps(props) {
        return {
            threadId: props.threadId,
            threadModel: props.threadModel,
        };
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
        mailPopoutService.popout(PopoutAttachmentView, extractPopoutProps(component.props));
    }

    function updatePopout(newProps = component.props) {
        if (mailPopoutService.externalWindow) {
            hideAttachmentView();
            mailPopoutService.popout(PopoutAttachmentView, extractPopoutProps(newProps));
        }
    }

    function resetPopout() {
        mailPopoutService.reset();
    }

    onMounted(updatePopout);
    onWillUpdateProps((props) => {
        const oldProps = extractPopoutProps(component.props);
        const newProps = extractPopoutProps(props);
        if (!deepEqual(oldProps, newProps)) {
            updatePopout(newProps);
        }
    });
    onWillUnmount(resetPopout);
    return {
        popout,
        updatePopout,
        resetPopout,
    };
}

/**
 * @typedef {Object} Props
 * @property {number} threadId
 * @property {string} threadModel
 * @extends {Component<Props, Env>}
 */
export class AttachmentView extends AbstractAttachmentView {
    setup() {
        super.setup();
        this.attachmentPopout = usePopoutAttachment();
    }

    onClickPopout() {
        this.attachmentPopout.popout();
    }
}
