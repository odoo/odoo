import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, useRef, useEffect, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { cleanZWChars, deduceURLfromText } from "./utils";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { isAbsoluteURLInCurrentDomain } from "@html_editor/utils/url";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import {
    BUTTON_SHAPES,
    BUTTON_SIZES,
    BUTTON_TYPES,
    computeButtonClasses,
    getButtonShape,
    getButtonSize,
    getButtonType,
} from "@html_editor/utils/button_style";

export class LinkPopover extends Component {
    static template = "html_editor.linkPopover";
    static props = {
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        linkElement: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        containerElement: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        ignoreDOMMutations: Function,
        onApply: Function,
        onChange: Function,
        onDiscard: Function,
        onRemove: Function,
        onCopy: Function,
        onEdit: Function,
        getInternalMetaData: Function,
        getExternalMetaData: Function,
        getAttachmentMetadata: Function,
        isImage: Boolean,
        showReplaceTitleBanner: Boolean,
        type: String,
        LinkPopoverState: Object,
        recordInfo: Object,
        canEdit: { type: Boolean, optional: true },
        canRemove: { type: Boolean, optional: true },
        canUpload: { type: Boolean, optional: true },
        onUpload: { type: Function, optional: true },
        includeStyling: { type: Boolean, optional: true },
        allowTargetBlank: { type: Boolean, optional: true },
        allowStripDomain: { type: Boolean, optional: true },
        relAttributeOptions: { type: Array, optional: true },
    };
    static defaultProps = {
        canEdit: true,
        canRemove: true,
        includeStyling: true,
    };
    static components = { CheckBox, Dropdown, DropdownItem };
    buttonSizesData = BUTTON_SIZES;
    buttonShapesData = BUTTON_SHAPES;
    buttonTypesData = BUTTON_TYPES;

    setup() {
        this.ui = useService("ui");
        this.notificationService = useService("notification");
        this.uploadService = useService("uploadLocalFiles");

        const linkElement = this.props.linkElement;
        const textContent = cleanZWChars(linkElement.textContent);
        const labelEqualsUrl =
            textContent === linkElement.getAttribute("href") ||
            textContent + "/" === linkElement.getAttribute("href");

        this.linkPreviewTarget =
            linkElement.hash?.length && this.isAbsoluteURLInCurrentDomain(linkElement.href)
                ? "_self"
                : "_blank";

        this.state = useState({
            editing: this.props.LinkPopoverState.editing,
            // `.getAttribute("href")` instead of `.href` to keep relative url
            url: linkElement.getAttribute("href") || this.deduceUrl(textContent),
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
            type: this.props.type || getButtonType(linkElement),
            directDownload: true,
            isDocument: false,
            buttonSize: getButtonSize(linkElement),
            buttonShape: getButtonShape(linkElement),
            isImage: this.props.isImage,
            showReplaceTitleBanner: this.props.showReplaceTitleBanner,
            showLabel: !linkElement.childElementCount,
            stripDomain: true,
        });

        this.updateDocumentState();
        this.editingWrapper = useRef("editing-wrapper");
        this.inputRef = useRef(
            this.state.isImage || (this.state.label && !this.state.url) ? "url" : "label"
        );
        useEffect(
            (el) => {
                if (el) {
                    el.focus();
                }
            },
            () => [this.inputRef.el]
        );
        if (!this.state.editing) {
            this.loadAsyncLinkPreview();
        }
        const onPointerDown = (ev) => {
            if (this.state.isImage) {
                return;
            }
            this.state.url ||= "#";
            if (this.editingWrapper?.el && !this.editingWrapper.el.contains(ev.target)) {
                this.onClickApply();
            }
        };
        useExternalListener(this.props.document, "pointerdown", onPointerDown);
        if (this.props.document !== document) {
            // Listen to pointerdown outside the iframe
            useExternalListener(document, "pointerdown", onPointerDown);
        }
    }

    prepareParams() {
        return {
            url: this.state.url,
            label: this.state.label,
            classes: this.classes,
            customStyle: this.customStyles,
            attachmentId: this.state.attachmentId,
        };
    }

    onChange() {
        // Apply changes to update the link preview.
        const params = this.prepareParams();
        this.props.onChange(params);
        this.updateDocumentState();
    }
    onClickApply() {
        this.state.editing = false;
        this.applyDeducedUrl();
        const params = this.prepareParams();
        this.props.onApply(params);
    }
    applyDeducedUrl() {
        if (this.state.label === "") {
            this.state.label = this.state.url;
        }
        const deducedUrl = this.deduceUrl(this.state.url);
        this.state.url = deducedUrl
            ? this.correctLink(deducedUrl)
            : this.correctLink(this.state.url);
        if (
            this.props.allowStripDomain &&
            this.state.stripDomain &&
            this.isAbsoluteURLInCurrentDomain()
        ) {
            const urlObj = new URL(this.state.url, window.location.origin);
            // Not necessarily equal to window.location.origin
            // (see isAbsoluteURLInCurrentDomain)
            this.state.url = this.state.url.replace(urlObj.origin, "");
        }
    }
    onClickEdit() {
        this.state.editing = true;
        this.props.onEdit();
        this.updateUrlAndLabel();
    }
    updateUrlAndLabel() {
        this.state.url = this.props.linkElement.getAttribute("href");

        const textContent = cleanZWChars(this.props.linkElement.textContent);
        const labelEqualsUrl =
            textContent === this.props.linkElement.getAttribute("href") ||
            textContent + "/" === this.props.linkElement.getAttribute("href");
        this.state.label = labelEqualsUrl ? "" : textContent;
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
            ev.stopImmediatePropagation();
            this.onClickApply();
        } else if (ev.key == "Tab") {
            ev.preventDefault();
            const focusableElements = [
                ...this.editingWrapper.el.querySelectorAll("input, select, button:not([disabled])"),
            ];
            const currentIndex = focusableElements.indexOf(document.activeElement);
            const nextIndex =
                (currentIndex + (ev.shiftKey ? -1 : 1) + focusableElements.length) %
                focusableElements.length;
            focusableElements[nextIndex].focus();
        }
    }

    onInput() {
        this.onChange();
    }

    onClickReplaceTitle() {
        this.state.label = this.state.urlTitle;
        this.onClickApply();
    }

    onClickDirectDownload(checked) {
        this.state.directDownload = checked;
        this.state.url = this.state.url.replace("&download=true", "");
        if (this.state.directDownload) {
            this.state.url += "&download=true";
        }
    }

    onClickStripDomain(checked) {
        this.state.stripDomain = checked;
    }

    /**
     * Updates the component state with the chosen link type and triggers
     * `onChange` to propagate the update.
     *
     * @param {string} type - The selected link type
     */
    onSelectedLinkType(type) {
        this.state.type = type;
        this.onChange();
    }

    /**
     * @private
     */
    async updateDocumentState() {
        const url = this.state.url;
        const urlObject = URL.parse(url, document.URL);
        if (
            url &&
            (url.startsWith("/web/content/") ||
                (urlObject &&
                    urlObject.pathname.startsWith("/web/content") &&
                    urlObject.host === document.location.host))
        ) {
            const { type } = await this.props.getAttachmentMetadata(url);
            this.state.isDocument = type !== "url";
            this.state.directDownload = url.includes("&download=true");
        } else {
            this.state.isDocument = false;
            this.state.directDownload = true;
        }
    }
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
        if (url && (url.startsWith("http:") || url.startsWith("https:"))) {
            url = URL.parse(url) ? url : "";
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
        if (this.isLogoutUrl()) {
            // The session ends if we fetch this url, so the preview is hardcoded
            this.resetPreview();
            this.state.urlTitle = _t("Logout");
            this.state.previewIcon.value = "fa-sign-out";
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
            url = new URL(this.state.url, document.URL); // relative to absolute
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

            const externalMetadata = await this.props
                .getExternalMetaData(this.state.url)
                .catch((error) => {
                    console.warn(`Error fetching external metadata for ${url.href}:`, error);
                    return {};
                });

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
            const internalMetadata = await this.props
                .getInternalMetaData(url.href)
                .catch((error) => {
                    console.warn(`Error fetching internal metadata for ${url.href}:`, error);
                    return {};
                });
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

            if (internalMetadata.imgSrc) {
                this.state.imgSrc = internalMetadata.imgSrc;
                this.state.previewIcon = {
                    type: "fa",
                    value: "fa-picture-o",
                };
            }
        }
    }

    get classes() {
        return computeButtonClasses(this.props.linkElement, {
            type: this.state.type,
            size: this.state.buttonSize,
            shape: this.state.buttonShape,
        });
    }

    get showUrl() {
        return this.state.urlTitle && this.state.url && this.state.urlTitle !== this.state.url;
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

    isLogoutUrl() {
        return !!this.state.url.match(/\/web\/session\/logout\b/);
    }
    isAttachmentUrl() {
        return !!this.state.url.match(/\/web\/content\/\d+/);
    }

    isAbsoluteURLInCurrentDomain(url = this.state.url) {
        return isAbsoluteURLInCurrentDomain(url);
    }
}
