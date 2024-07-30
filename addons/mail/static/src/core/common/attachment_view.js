import {
    Component,
    onWillUpdateProps,
    onPatched,
    onWillUnmount,
    onMounted,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { hidePDFJSButtons } from "@web/libs/pdfjs";

/**
 * @typedef {Object} Props
 * @property {number} threadId
 * @property {string} threadModel
 * @extends {Component<Props, Env>}
 */
export class AttachmentView extends Component {
    static template = "mail.AttachmentView";
    static components = {};
    static props = ["threadId", "threadModel"];

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.uiService = useService("ui");
        this.mailPopoutService = useService("mail.popout");
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

        onMounted(this.updatePopout);
        onPatched(this.updatePopout);
        onWillUnmount(this.resetPopout);
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

    popoutAttachment() {
        this.mailPopoutService.addHooks(
            () => {
                // before popout hook
                this.hide();
                this.uiService.bus.trigger("resize");
            },
            () => {
                // after popout hook
                this.show();
                this.uiService.bus.trigger("resize");
            }
        );
        this.mailPopoutService.popout(PopoutAttachmentView, this.props);
    }

    get attachmentViewParentElementClassList() {
        const attachmentViewEl = document.querySelector(".o-mail-Attachment");
        let parentElementClassList;
        if ((parentElementClassList = attachmentViewEl?.parentElement?.classList)) {
            return parentElementClassList;
        }
        return null;
    }

    show() {
        const parentElementClassList = this.attachmentViewParentElementClassList;
        const hiddenClass = "d-none";
        if (parentElementClassList?.contains(hiddenClass)) {
            parentElementClassList.remove(hiddenClass);
        }
    }

    hide() {
        const parentElementClassList = this.attachmentViewParentElementClassList;
        const hiddenClass = "d-none";
        if (!parentElementClassList?.contains(hiddenClass)) {
            parentElementClassList.add(hiddenClass);
        }
    }

    updatePopout() {
        if (this.mailPopoutService.externalWindow) {
            this.mailPopoutService.popout(PopoutAttachmentView, this.props);
            this.hide();
        }
    }

    resetPopout() {
        this.mailPopoutService.reset();
    }

    get displayName() {
        return this.state.thread.mainAttachment.filename;
    }
}

/*
 * AttachmentView inside popout window.
 * Popout features disabled as this only makes sense in the non-popout AttachmentView.
 */
class PopoutAttachmentView extends AttachmentView {
    static template = "mail.PopoutAttachmentView";
    updatePopout() {}
    resetPopout() {}
}
