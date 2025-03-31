import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { KeepLast } from "@web/core/utils/concurrency";
import { useDebounced } from "@web/core/utils/timing";
import { SearchMedia } from "./search_media";

import { Component, xml, useState, useRef, onWillStart, useEffect } from "@odoo/owl";

export const IMAGE_MIMETYPES = [
    "image/jpg",
    "image/jpeg",
    "image/jpe",
    "image/png",
    "image/svg+xml",
    "image/gif",
    "image/webp",
];
export const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".jpe", ".png", ".svg", ".gif", ".webp"];

class RemoveButton extends Component {
    static template = xml`<i class="fa fa-trash o_existing_attachment_remove position-absolute top-0 end-0 p-2 bg-white-25 cursor-pointer opacity-0 opacity-100-hover z-index-1 transition-base" t-att-title="removeTitle" role="img" t-att-aria-label="removeTitle" t-on-click="this.remove"/>`;
    static props = ["model?", "remove"];
    setup() {
        this.removeTitle = _t("This file is attached to the current record.");
        if (this.props.model === "ir.ui.view") {
            this.removeTitle = _t("This file is a public view attachment.");
        }
    }

    remove(ev) {
        ev.stopPropagation();
        this.props.remove();
    }
}

export class AttachmentError extends Component {
    static components = { Dialog };
    static template = xml`
        <Dialog title="title">
            <div class="form-text">
                <p>The image could not be deleted because it is used in the
                    following pages or views:</p>
                <ul t-foreach="props.views"  t-as="view" t-key="view.id">
                    <li>
                        <a t-att-href="'/odoo/ir.ui.view/' + window.encodeURIComponent(view.id)">
                            <t t-esc="view.name"/>
                        </a>
                    </li>
                </ul>
            </div>
            <t t-set-slot="footer">
                <button class="btn btn-primary" t-on-click="() => this.props.close()">
                    Ok
                </button>
            </t>
        </Dialog>`;
    static props = ["views", "close"];
    setup() {
        this.title = _t("Alert");
    }
}

export class Attachment extends Component {
    static template = "";
    static components = {
        RemoveButton,
    };
    static props = ["*"];
    setup() {
        this.dialogs = useService("dialog");
    }

    remove() {
        this.dialogs.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this file?"),
            confirm: async () => {
                const prevented = await rpc("/web_editor/attachment/remove", {
                    ids: [this.props.id],
                });
                if (!Object.keys(prevented).length) {
                    this.props.onRemoved(this.props.id);
                } else {
                    this.dialogs.add(AttachmentError, {
                        views: prevented[this.props.id],
                    });
                }
            },
        });
    }
}

export class FileSelectorControlPanel extends Component {
    static template = "html_editor.FileSelectorControlPanel";
    static components = {
        SearchMedia,
    };
    static props = {
        uploadUrl: Function,
        validateUrl: Function,
        uploadFiles: Function,
        changeSearchService: Function,
        changeShowOptimized: Function,
        search: Function,
        accept: { type: String, optional: true },
        addText: { type: String, optional: true },
        multiSelect: { type: true, optional: true },
        needle: { type: String, optional: true },
        searchPlaceholder: { type: String, optional: true },
        searchService: { type: String, optional: true },
        showOptimized: { type: Boolean, optional: true },
        showOptimizedOption: { type: String, optional: true },
        uploadText: { type: String, optional: true },
        urlPlaceholder: { type: String, optional: true },
        urlWarningTitle: { type: String, optional: true },
        useMediaLibrary: { type: Boolean, optional: true },
        useUnsplash: { type: Boolean, optional: true },
    };
    setup() {
        this.state = useState({
            showUrlInput: false,
            urlInput: "",
            isValidUrl: false,
            isValidFileFormat: false,
            isValidatingUrl: false,
        });
        this.debouncedValidateUrl = useDebounced(this.props.validateUrl, 500);

        this.fileInput = useRef("file-input");
    }

    get showSearchServiceSelect() {
        return this.props.searchService && this.props.needle;
    }

    get enableUrlUploadClick() {
        return (
            !this.state.showUrlInput ||
            (this.state.urlInput && this.state.isValidUrl && this.state.isValidFileFormat)
        );
    }

    async onUrlUploadClick() {
        if (!this.state.showUrlInput) {
            this.state.showUrlInput = true;
        } else {
            await this.props.uploadUrl(this.state.urlInput);
            this.state.urlInput = "";
        }
    }

    async onUrlInput(ev) {
        this.state.isValidatingUrl = true;
        const { isValidUrl, isValidFileFormat } = await this.debouncedValidateUrl(ev.target.value);
        this.state.isValidFileFormat = isValidFileFormat;
        this.state.isValidUrl = isValidUrl;
        this.state.isValidatingUrl = false;
    }

    onClickUpload() {
        this.fileInput.el.click();
    }

    async onChangeFileInput() {
        const inputFiles = this.fileInput.el.files;
        if (!inputFiles.length) {
            return;
        }
        await this.props.uploadFiles(inputFiles);
        this.fileInput.el.value = "";
    }
}

export class FileSelector extends Component {
    static template = "html_editor.FileSelector";
    static components = {
        FileSelectorControlPanel,
    };
    static props = ["*"];

    setup() {
        this.notificationService = useService("notification");
        this.orm = useService("orm");
        this.uploadService = useService("upload");
        this.keepLast = new KeepLast();

        this.loadMoreButtonRef = useRef("load-more-button");
        this.existingAttachmentsRef = useRef("existing-attachments");

        this.state = useState({
            attachments: [],
            canScrollAttachments: false,
            canLoadMoreAttachments: false,
            isFetchingAttachments: false,
            needle: "",
        });

        this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY = 30;

        onWillStart(async () => {
            this.state.attachments = await this.fetchAttachments(
                this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY,
                0
            );
        });

        this.debouncedOnScroll = useDebounced(this.updateScroll, 15);
        this.debouncedScrollUpdate = useDebounced(this.updateScroll, 500);

        useEffect(
            (modalEl) => {
                if (modalEl) {
                    modalEl.addEventListener("scroll", this.debouncedOnScroll);
                    return () => {
                        modalEl.removeEventListener("scroll", this.debouncedOnScroll);
                    };
                }
            },
            () => [this.props.modalRef.el?.querySelector("main.modal-body")]
        );

        useEffect(
            () => {
                // Updating the scroll button each time the attachments change.
                // Hiding the "Load more" button to prevent it from flickering.
                this.loadMoreButtonRef.el.classList.add("o_hide_loading");
                this.state.canScrollAttachments = false;
                this.debouncedScrollUpdate();
            },
            () => [this.allAttachments.length]
        );
    }

    get canLoadMore() {
        return this.state.canLoadMoreAttachments;
    }

    get hasContent() {
        return this.state.attachments.length;
    }

    get isFetching() {
        return this.state.isFetchingAttachments;
    }

    get selectedAttachmentIds() {
        return this.props.selectedMedia[this.props.id]
            .filter((media) => media.mediaType === "attachment")
            .map(({ id }) => id);
    }

    get attachmentsDomain() {
        const domain = [
            "&",
            ["res_model", "=", this.props.resModel],
            ["res_id", "=", this.props.resId || 0],
        ];
        domain.unshift("|", ["public", "=", true]);
        domain.push(["name", "ilike", this.state.needle]);
        return domain;
    }

    get allAttachments() {
        return this.state.attachments;
    }

    validateUrl(url) {
        const path = url.split("?")[0];
        const isValidUrl = /^.+\..+$/.test(path); // TODO improve
        const isValidFileFormat = true;
        return { isValidUrl, isValidFileFormat, path };
    }

    async fetchAttachments(limit, offset) {
        this.state.isFetchingAttachments = true;
        let attachments = [];
        try {
            attachments = await this.orm.call("ir.attachment", "search_read", [], {
                domain: this.attachmentsDomain,
                fields: [
                    "name",
                    "mimetype",
                    "description",
                    "checksum",
                    "url",
                    "type",
                    "res_id",
                    "res_model",
                    "public",
                    "access_token",
                    "image_src",
                    "image_width",
                    "image_height",
                    "original_id",
                ],
                order: "id desc",
                // Try to fetch first record of next page just to know whether there is a next page.
                limit,
                offset,
            });
            attachments.forEach((attachment) => (attachment.mediaType = "attachment"));
        } catch (e) {
            // Reading attachments as a portal user is not permitted and will raise
            // an access error so we catch the error silently and don't return any
            // attachment so he can still use the wizard and upload an attachment
            if (e.exceptionName !== "odoo.exceptions.AccessError") {
                throw e;
            }
        }
        this.state.canLoadMoreAttachments =
            attachments.length >= this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY;
        this.state.isFetchingAttachments = false;
        return attachments;
    }

    async handleLoadMore() {
        await this.loadMore();
    }

    async loadMore() {
        return this.keepLast
            .add(
                this.fetchAttachments(
                    this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY,
                    this.state.attachments.length
                )
            )
            .then((newAttachments) => {
                // This is never reached if another search or loadMore occurred.
                this.state.attachments.push(...newAttachments);
            });
    }

    async handleSearch(needle) {
        await this.search(needle);
    }

    async search(needle) {
        // Prepare in case loadMore results are obtained instead.
        this.state.attachments = [];
        // Fetch attachments relies on the state's needle.
        this.state.needle = needle;
        return this.keepLast
            .add(this.fetchAttachments(this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY, 0))
            .then((attachments) => {
                // This is never reached if a new search occurred.
                this.state.attachments = attachments;
            });
    }

    async uploadFiles(files) {
        await this.uploadService.uploadFiles(
            files,
            { resModel: this.props.resModel, resId: this.props.resId },
            (attachment) => this.onUploaded(attachment)
        );
    }

    async uploadUrl(url) {
        await fetch(url)
            .then(async (result) => {
                const blob = await result.blob();
                blob.id = new Date().getTime();
                blob.name = new URL(url).pathname.split("/").findLast((s) => s);
                await this.uploadFiles([blob]);
            })
            .catch(async () => {
                await new Promise((resolve) => {
                    // If it works from an image, use URL.
                    const imageEl = document.createElement("img");
                    imageEl.onerror = () => {
                        // This message is about the blob fetch failure.
                        // It is only displayed if the fallback did not work.
                        this.notificationService.add(
                            _t("An error occurred while fetching the entered URL."),
                            {
                                title: _t("Error"),
                                sticky: true,
                            }
                        );
                        resolve();
                    };
                    imageEl.onload = () => {
                        this.uploadService
                            .uploadUrl(
                                url,
                                {
                                    resModel: this.props.resModel,
                                    resId: this.props.resId,
                                },
                                (attachment) => this.onUploaded(attachment)
                            )
                            .then(resolve);
                    };
                    imageEl.src = url;
                });
            });
    }

    async onUploaded(attachment) {
        this.state.attachments = [
            attachment,
            ...this.state.attachments.filter((attach) => attach.id !== attachment.id),
        ];
        this.selectAttachment(attachment);
        if (!this.props.multiSelect) {
            await this.props.save();
        }
        if (this.props.onAttachmentChange) {
            this.props.onAttachmentChange(attachment);
        }
    }

    onRemoved(attachmentId) {
        this.state.attachments = this.state.attachments.filter(
            (attachment) => attachment.id !== attachmentId
        );
    }

    selectAttachment(attachment) {
        this.props.selectMedia({ ...attachment, mediaType: "attachment" });
    }

    selectInitialMedia() {
        return (
            this.props.media &&
            this.constructor.tagNames.includes(this.props.media.tagName) &&
            !this.selectedAttachmentIds.length
        );
    }

    /**
     * Updates the scroll button, depending on whether the "Load more" button is
     * fully visible or not.
     */
    updateScroll() {
        const loadMoreTop = this.loadMoreButtonRef.el.getBoundingClientRect().top;
        const modalEl = this.props.modalRef.el.querySelector("main.modal-body");
        const modalBottom = modalEl.getBoundingClientRect().bottom;
        this.state.canScrollAttachments = loadMoreTop >= modalBottom;
        this.loadMoreButtonRef.el.classList.remove("o_hide_loading");
    }

    /**
     * Checks if the attachment is (partially) hidden.
     *
     * @param {Element} attachmentEl the attachment "container"
     * @returns {Boolean} true if the attachment is hidden, false otherwise.
     */
    isAttachmentHidden(attachmentEl) {
        const attachmentBottom = Math.round(attachmentEl.getBoundingClientRect().bottom);
        const modalEl = this.props.modalRef.el.querySelector("main.modal-body");
        const modalBottom = modalEl.getBoundingClientRect().bottom;
        return attachmentBottom > modalBottom;
    }

    /**
     * Scrolls two attachments rows at a time. If there are not enough rows,
     * scrolls to the "Load more" button.
     */
    handleScrollAttachments() {
        let scrollToEl = this.loadMoreButtonRef.el;
        const attachmentEls = [
            ...this.existingAttachmentsRef.el.querySelectorAll(".o_existing_attachment_cell"),
        ];
        const firstHiddenAttachmentEl = attachmentEls.find((el) => this.isAttachmentHidden(el));
        if (firstHiddenAttachmentEl) {
            const attachmentBottom = firstHiddenAttachmentEl.getBoundingClientRect().bottom;
            const attachmentIndex = attachmentEls.indexOf(firstHiddenAttachmentEl);
            const firstNextRowAttachmentEl = attachmentEls.slice(attachmentIndex).find((el) => {
                return el.getBoundingClientRect().bottom > attachmentBottom;
            });
            scrollToEl = firstNextRowAttachmentEl || scrollToEl;
        }
        scrollToEl.scrollIntoView({ block: "end", inline: "nearest", behavior: "smooth" });
    }
}
