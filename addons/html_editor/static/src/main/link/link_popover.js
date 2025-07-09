import { _t } from "@web/core/l10n/translation";
import { Component, useState, onMounted, useRef, useEffect, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { cleanZWChars, deduceURLfromText } from "./utils";
import { useColorPicker } from "@web/core/color_picker/color_picker";
import { CheckBox } from "@web/core/checkbox/checkbox";

const DEFAULT_CUSTOM_TEXT_COLOR = "#714B67";
const DEFAULT_CUSTOM_FILL_COLOR = "#ffffff";

export class LinkPopover extends Component {
    static template = "html_editor.linkPopover";
    static props = {
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
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
        showReplaceTitleBanner: Boolean,
        type: String,
        LinkPopoverState: Object,
        recordInfo: Object,
        canEdit: { type: Boolean, optional: true },
        canRemove: { type: Boolean, optional: true },
        canUpload: { type: Boolean, optional: true },
        onUpload: { type: Function, optional: true },
        allowCustomStyle: { type: Boolean, optional: true },
        allowTargetBlank: { type: Boolean, optional: true },
    };
    static defaultProps = {
        canEdit: true,
        canRemove: true,
    };
    static components = { CheckBox };
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
    buttonSizesData = [
        { size: "sm", label: _t("Small") },
        { size: "", label: _t("Medium") },
        { size: "lg", label: _t("Large") },
    ];
    borderData = [
        { style: "solid", label: "━━━" },
        { style: "dashed", label: "╌╌╌" },
        { style: "dotted", label: "┄┄┄" },
        { style: "double", label: "═══" },
    ];
    setup() {
        this.ui = useService("ui");
        this.notificationService = useService("notification");
        this.uploadService = useService("uploadLocalFiles");

        const textContent = cleanZWChars(this.props.linkElement.textContent);
        const labelEqualsUrl =
            textContent === this.props.linkElement.getAttribute("href") ||
            textContent + "/" === this.props.linkElement.getAttribute("href");
        const computedStyle = this.props.document.defaultView.getComputedStyle(
            this.props.linkElement
        );
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
                    .match(/btn(-[a-z0-9_-]*)(primary|secondary|custom)/)
                    ?.pop() ||
                "",
            linkTarget: this.props.linkElement.target === "_blank" ? "_blank" : "",
            directDownload: true,
            isDocument: false,
            buttonSize: this.props.linkElement.className.match(/btn-(sm|lg)/)?.[1] || "",
            customBorderSize: computedStyle.borderWidth.replace("px", "") || "1",
            customBorderStyle: computedStyle.borderStyle || "solid",
            isImage: this.props.isImage,
            showReplaceTitleBanner: this.props.showReplaceTitleBanner,
            showLabel: !this.props.linkElement.childElementCount,
        });

        this.customTextColorState = useState({
            selectedColor: computedStyle.color || DEFAULT_CUSTOM_TEXT_COLOR,
            defaultTab: "solid",
        });
        this.customTextResetPreviewColor = this.customTextColorState.selectedColor;
        this.customFillColorState = useState({
            selectedColor: computedStyle.backgroundColor || DEFAULT_CUSTOM_FILL_COLOR,
            defaultTab: "solid",
        });
        this.customFillResetPreviewColor = this.customFillColorState.selectedColor;
        this.customBorderColorState = useState({
            selectedColor: computedStyle.borderColor || DEFAULT_CUSTOM_TEXT_COLOR,
            defaultTab: "solid",
        });
        this.customBorderResetPreviewColor = this.customBorderColorState.selectedColor;

        if (this.props.allowCustomStyle) {
            const createCustomColorPicker = (refName, colorStateRef, resetValueRef) =>
                useColorPicker(
                    refName,
                    {
                        state: this[colorStateRef],
                        getUsedCustomColors: () => [],
                        colorPrefix: "",
                        applyColor: (colorValue) => {
                            this[colorStateRef].selectedColor = colorValue;
                            this[resetValueRef] = colorValue;
                        },
                        applyColorPreview: (colorValue) => {
                            this[colorStateRef].selectedColor = colorValue;
                        },
                        applyColorResetPreview: () => {
                            this[colorStateRef].selectedColor = this[resetValueRef];
                        },
                    },
                    {
                        onClose: this.onChange.bind(this),
                    }
                );
            this.customTextColorPicker = createCustomColorPicker(
                "customTextColorButton",
                "customTextColorState",
                "customTextResetPreviewColor"
            );
            this.customFillColorPicker = createCustomColorPicker(
                "customFillColorButton",
                "customFillColorState",
                "customFillResetPreviewColor"
            );
            this.customBorderColorPicker = createCustomColorPicker(
                "customBorderColorButton",
                "customBorderColorState",
                "customBorderResetPreviewColor"
            );
        }
        this.updateDocumentState();
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
        const onPointerDown = (ev) => {
            if (!this.state.url) {
                this.props.onDiscard();
            } else if (
                this.editingWrapper?.el &&
                !this.state.isImage &&
                !this.editingWrapper.el.contains(ev.target)
            ) {
                this.onClickApply();
            }
        };
        useExternalListener(this.props.document, "pointerdown", onPointerDown);
        if (this.props.document !== document) {
            // Listen to pointerdown outside the iframe
            useExternalListener(document, "pointerdown", onPointerDown);
        }
    }

    onChange() {
        // Apply changes to update the link preview.
        this.props.onChange(
            this.state.url,
            this.state.label,
            this.classes,
            this.customStyles,
            this.state.linkTarget,
            this.state.attachmentId
        );
        this.updateDocumentState();
    }
    onClickApply() {
        this.state.editing = false;
        this.applyDeducedUrl();
        this.props.onApply(
            this.state.url,
            this.state.label,
            this.classes,
            this.customStyles,
            this.state.linkTarget,
            this.state.attachmentId
        );
    }
    applyDeducedUrl() {
        if (this.state.label === "") {
            this.state.label = this.state.url;
        }
        const deducedUrl = this.deduceUrl(this.state.url);
        this.state.url = deducedUrl
            ? this.correctLink(deducedUrl)
            : this.correctLink(this.state.url);
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
            ev.stopImmediatePropagation();
            this.props.onClose();
        }
    }

    onClickReplaceTitle() {
        this.state.label = this.state.urlTitle;
        this.onClickApply();
    }

    onClickForceEditMode(ev) {
        if (this.props.linkElement.href) {
            const currentUrl = new URL(this.props.linkElement.href);
            if (
                browser.location.hostname === currentUrl.hostname &&
                !currentUrl.pathname.startsWith("/@/")
            ) {
                ev.preventDefault();
                currentUrl.pathname = `/@${currentUrl.pathname}`;
                browser.open(currentUrl);
            }
        }
    }

    onClickDirectDownload(checked) {
        this.state.directDownload = checked;
        this.state.url = this.state.url.replace("&download=true", "");
        if (this.state.directDownload) {
            this.state.url += "&download=true";
        }
    }

    onClickNewWindow(checked) {
        this.state.linkTarget = checked ? "_blank" : "";
    }

    /**
     * @private
     */
    async updateDocumentState() {
        const url = this.state.url;
        const urlObject = URL.parse(url, this.props.document.URL);
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
            url = new URL(this.state.url, this.props.document.URL); // relative to absolute
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
        } else if (window.location.hostname !== url.hostname) {
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
        let classes = [...this.props.linkElement.classList]
            .filter((value) => !value.match(/btn(-[a-z0-9]+)*/))
            .join(" ");

        if (this.state.type) {
            classes += ` btn btn-fill-${this.state.type}`;
        }

        if (this.state.buttonSize) {
            classes += ` btn-${this.state.buttonSize}`;
        }

        return classes.trim();
    }

    get customStyles() {
        if (!this.props.allowCustomStyle || this.state.type !== "custom") {
            return false;
        }
        let customStyles = `color: ${this.customTextColorState.selectedColor}; `;
        customStyles += `background-color: ${this.customFillColorState.selectedColor}; `;
        customStyles += `border-width: ${this.state.customBorderSize}px; `;
        customStyles += `border-color: ${this.customBorderColorState.selectedColor}; `;
        customStyles += `border-style: ${this.state.customBorderStyle}; `;

        return customStyles;
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
}
