import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onMounted, useRef, useEffect, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { cleanZWChars, deduceURLfromText } from "./utils";

export class LinkPopover extends Component {
    static template = "html_editor.linkPopover";
    static props = {
        linkElement: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        onApply: Function,
        onChange: Function,
        onDiscard: Function,
        onRemove: Function,
        onCopy: Function,
        onClose: Function,
        onEdit: Function,
        getInternalMetaData: Function,
        getExternalMetaData: Function,
        getAttachmentMetadata: Function,
        isImage: Boolean,
        type: String,
        LinkPopoverState: Object,
        recordInfo: Object,
        canEdit: { type: Boolean, optional: true },
        canUpload: { type: Boolean, optional: true },
        onUpload: { type: Function, optional: true },
    };
    static defaultProps = {
        canEdit: true,
    };
    colorsData = [
        { type: "", label: _t("Link"), btnPreview: "link" },
        { type: "primary", label: _t("Button Primary"), btnPreview: "primary" },
        { type: "secondary", label: _t("Button Secondary"), btnPreview: "secondary" },
        { type: "custom", label: _t("Custom"), btnPreview: "custom" },
        // Note: by compatibility the dialog should be able to remove old
        // colors that were suggested like the BS status colors or the
        // alpha -> epsilon classes. This is currently done by removing
        // all btn-* classes anyway.
    ];
    setup() {
        this.ui = useService("ui");
        this.notificationService = useService("notification");
        this.uploadService = useService("uploadLocalFiles");

        const textContent = cleanZWChars(this.props.linkElement.textContent);
        const labelEqualsUrl =
            textContent === this.props.linkElement.getAttribute("href") ||
            textContent + "/" === this.props.linkElement.getAttribute("href");
        this.state = useState({
            editing: this.props.LinkPopoverState.editing,
            // `.getAttribute("href")` instead of `.href` to keep relative url
            url: this.props.linkElement.getAttribute("href") || this.deduceUrl(textContent),
            label: labelEqualsUrl ? "" : textContent,
            previewIcon: {
                /** @type {'fa'|'imgSrc'|'mimetype'} */
                type: "fa",
                value: "fa-globe",
            },
            urlTitle: "",
            urlDescription: "",
            linkPreviewName: "",
            imgSrc: "",
            type:
                this.props.type ||
                this.props.linkElement.className
                    .match(/btn(-[a-z0-9_-]*)(primary|secondary)/)
                    ?.pop() ||
                "",
            isImage: this.props.isImage,
            showLabel: !this.props.linkElement.childElementCount,
        });

        this.editingWrapper = useRef("editing-wrapper");
        this.inputRef = useRef(this.state.isImage ? "url" : "label");
        useEffect(
            (el) => {
                if (el) {
                    el.focus();
                }
            },
            () => [this.inputRef.el]
        );
        onMounted(() => {
            if (!this.state.editing) {
                this.loadAsyncLinkPreview();
            }
        });
        useExternalListener(document, "pointerdown", (ev) => {
            if (!this.state.url) {
                this.props.onDiscard();
            } else if (
                this.editingWrapper?.el &&
                !this.state.isImage &&
                !this.editingWrapper.el.contains(ev.target)
            ) {
                this.onClickApply();
            }
        });
    }

    onChange() {
        // Apply changes to update the link preview.
        this.props.onChange(
            this.state.url,
            this.state.label,
            this.classes,
            this.state.attachmentId
        );
    }
    onClickApply() {
        this.state.editing = false;
        if (this.state.label === "") {
            this.state.label = this.state.url;
        }
        const deducedUrl = this.deduceUrl(this.state.url);
        this.state.url = deducedUrl
            ? this.correctLink(deducedUrl)
            : this.correctLink(this.state.url);
        this.props.onApply(this.state.url, this.state.label, this.classes, this.state.attachmentId);
    }
    onClickEdit() {
        this.state.editing = true;
        this.props.onEdit();
        this.state.url = this.props.linkElement.getAttribute("href");

        const textContent = cleanZWChars(this.props.linkElement.textContent);
        const labelEqualsUrl =
            textContent === this.props.linkElement.getAttribute("href") ||
            textContent + "/" === this.props.linkElement.getAttribute("href");
        this.state.label = labelEqualsUrl ? "" : textContent;
    }
    async onClickCopy(ev) {
        ev.preventDefault();
        await browser.navigator.clipboard.writeText(this.props.linkElement.href || "");
        this.notificationService.add(_t("Link copied to clipboard."), {
            type: "success",
        });
        this.props.onCopy();
    }
    onClickRemove() {
        this.props.onRemove();
    }

    onKeydownEnter(ev) {
        const isAutoCompleteDropdownOpen = document.querySelector(".o-autocomplete--dropdown-menu");
        if (ev.key === "Enter" && !isAutoCompleteDropdownOpen && this.state.url) {
            ev.preventDefault();
            this.onClickApply();
        }
    }

    onKeydown(ev) {
        if (ev.key === "Escape") {
            ev.preventDefault();
            this.props.onClose();
        }
    }

    onClickReplaceTitle() {
        this.state.label = this.state.urlTitle;
        this.onClickApply();
    }

    /**
     * @private
     */
    correctLink(url) {
        if (
            url &&
            !url.startsWith("tel:") &&
            !url.startsWith("mailto:") &&
            !url.includes("://") &&
            !url.startsWith("/") &&
            !url.startsWith("#") &&
            !url.startsWith("${")
        ) {
            url = "https://" + url;
        }
        return url;
    }
    deduceUrl(text) {
        text = text.trim();
        if (/^(https?:|mailto:|tel:)/.test(text)) {
            // Text begins with a known protocol, accept it as valid URL.
            return text;
        } else {
            return deduceURLfromText(text, this.props.linkElement) || "";
        }
    }
    /**
     * link preview in the popover
     */
    resetPreview() {
        this.state.previewIcon = { type: "fa", value: "fa-globe" };
        this.state.urlTitle = this.state.url || _t("No URL specified");
        this.state.urlDescription = "";
        this.state.linkPreviewName = "";
    }
    async loadAsyncLinkPreview() {
        let url;
        if (this.state.url === "") {
            this.resetPreview();
            this.state.previewIcon.value = "fa-question-circle-o";
            return;
        }
        if (this.isAttachmentUrl()) {
            const { name, mimetype } = await this.props.getAttachmentMetadata(this.state.url);
            this.resetPreview();
            this.state.urlTitle = name;
            this.state.previewIcon = { type: "mimetype", value: mimetype };
            return;
        }

        try {
            url = new URL(this.state.url, this.props.linkElement.href); // relative to absolute
        } catch {
            // Invalid URL, might happen with editor unsuported protocol. eg type
            // `geo:37.786971,-122.399677`, become `http://geo:37.786971,-122.399677`
            this.notificationService.add(_t("This URL is invalid. Preview couldn't be updated."), {
                type: "danger",
            });
            return;
        }
        this.resetPreview();
        const protocol = url.protocol;
        if (!protocol.startsWith("http")) {
            const faMap = { "mailto:": "fa-envelope-o", "tel:": "fa-phone" };
            const icon = faMap[protocol];
            if (icon) {
                this.state.previewIcon.value = icon;
            }
        } else if (
            window.location.hostname !== url.hostname &&
            !new RegExp(`^https?://${session.db}\\.odoo\\.com(/.*)?$`).test(url.origin)
        ) {
            // Preview pages from current website only. External website will
            // most of the time raise a CORS error. To avoid that error, we
            // would need to fetch the page through the server (s2s), involving
            // enduser fetching problematic pages such as illicit content.
            this.state.previewIcon = {
                type: "imgSrc",
                value: `https://www.google.com/s2/favicons?sz=16&domain=${encodeURIComponent(url)}`,
            };

            const externalMetadata = await this.props.getExternalMetaData(this.state.url);

            this.state.urlTitle = externalMetadata?.og_title || this.state.url;
            this.state.urlDescription = externalMetadata?.og_description || "";
            this.state.imgSrc = externalMetadata?.og_image || "";
            if (
                externalMetadata?.og_image &&
                this.state.label &&
                this.state.urlTitle === this.state.url
            ) {
                this.state.urlTitle = this.state.label;
            }
        } else {
            // Set state based on cached link meta data
            // for record missing errors, we push a warning that the url is likely invalid
            // for other errors, we log them to not block the ui
            const internalMetadata = await this.props.getInternalMetaData(url.href);
            if (internalMetadata.favicon) {
                this.state.previewIcon = {
                    type: "imgSrc",
                    value: internalMetadata.favicon.href,
                };
            }
            if (internalMetadata.error_msg) {
                this.notificationService.add(internalMetadata.error_msg, {
                    type: "warning",
                });
            } else if (internalMetadata.other_error_msg) {
                console.error(
                    "Internal meta data retrieve error for link preview: " +
                        internalMetadata.other_error_msg
                );
            } else {
                this.state.linkPreviewName =
                    internalMetadata.link_preview_name ||
                    internalMetadata.display_name ||
                    internalMetadata.name;
                this.state.urlDescription = internalMetadata?.description || "";
                this.state.urlTitle = this.state.linkPreviewName
                    ? this.state.linkPreviewName
                    : this.state.url;
            }

            if (
                (internalMetadata.ogTitle || internalMetadata.title) &&
                !this.state.linkPreviewName
            ) {
                this.state.urlTitle = internalMetadata.ogTitle
                    ? internalMetadata.ogTitle.getAttribute("content")
                    : internalMetadata.title.text.trim();
            }
        }
    }

    get classes() {
        const className = [...this.props.linkElement.classList].filter(
            (value) => !value.match(/^(btn.*|rounded-circle|flat|(text|bg)-(o-color-\d$|\d{3}$))$/)
        );
        if (this.state.type) {
            className.push("btn", `btn-fill-${this.state.type}`);
        }
        return className.join(" ");
    }

    async uploadFile() {
        const { upload, getURL } = this.uploadService;
        const { resModel, resId } = this.props.recordInfo;
        const [attachment] = await upload({ resModel, resId, accessToken: true });
        if (!attachment) {
            // No file selected or upload failed
            return;
        }
        this.props.onUpload?.(attachment);
        this.state.url = getURL(attachment, { download: true, unique: true, accessToken: true });
        this.state.label ||= attachment.name;
        this.state.attachmentId = attachment.id;
        this.onChange();
    }

    isAttachmentUrl() {
        return !!this.state.url.match(/\/web\/content\/\d+/);
    }
}
