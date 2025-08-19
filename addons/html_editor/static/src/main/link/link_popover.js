import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, useRef, useEffect, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { cleanZWChars, deduceURLfromText } from "./utils";
import { useColorPicker } from "@web/core/color_picker/color_picker";
import { CheckBox } from "@web/core/checkbox/checkbox";

const DEFAULT_CUSTOM_TEXT_COLOR = "#714B67";
const DEFAULT_CUSTOM_FILL_COLOR = "#ffffff";

const isCSSVariable = (color) => color.match(/^o-color-\d$|^\d{3}$/);
const formatColor = (color) => {
    if (color.match(/^o-color-\d$/gm)) {
        return `var(--hb-cp-${color})`;
    }
    if (color.match(/^\d{3}$/gm)) {
        return `var(--${color})`;
    }
    return color;
};

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
        allowStripDomain: { type: Boolean, optional: true },
        formatColor: { type: Function, optional: true },
    };
    static defaultProps = {
        canEdit: true,
        canRemove: true,
        formatColor: formatColor,
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
    buttonShapeData = [
        { shape: "", label: "Default" },
        { shape: "rounded-circle", label: "Default + Rounded" },
        { shape: "outline", label: "Outline" },
        { shape: "outline rounded-circle", label: "Outline + Rounded" },
        { shape: "fill", label: "Fill" },
        { shape: "fill rounded-circle", label: "Fill + Rounded" },
        { shape: "flat", label: "Flat" },
    ];
    setup() {
        this.ui = useService("ui");
        this.notificationService = useService("notification");
        this.uploadService = useService("uploadLocalFiles");

        const linkElement = this.props.linkElement;
        const textContent = cleanZWChars(linkElement.textContent);
        const labelEqualsUrl =
            textContent === linkElement.getAttribute("href") ||
            textContent + "/" === linkElement.getAttribute("href");

        const computedStyle = this.props.document.defaultView.getComputedStyle(linkElement);
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
            type:
                this.props.type ||
                linkElement.className.match(/btn(-[a-z0-9_-]*)(primary|secondary|custom)/)?.pop() ||
                "",
            linkTarget: linkElement.target === "_blank" ? "_blank" : "",
            directDownload: true,
            isDocument: false,
            buttonSize: linkElement.className.match(/btn-(sm|lg)/)?.[1] || "",
            buttonShape: this.getButtonShape(),
            customBorderSize: computedStyle.borderWidth.replace("px", "") || "1",
            customBorderStyle: computedStyle.borderStyle || "solid",
            isImage: this.props.isImage,
            showReplaceTitleBanner: this.props.showReplaceTitleBanner,
            showLabel: !linkElement.childElementCount,
            stripDomain: true,
        });

        this.customTextColorState = useState({
            selectedColor: computedStyle.color || DEFAULT_CUSTOM_TEXT_COLOR,
            defaultTab: "solid",
        });
        this.customTextResetPreviewColor = this.customTextColorState.selectedColor;
        this.customFillColorState = useState({
            selectedColor:
                (computedStyle.backgroundImage === "none"
                    ? undefined
                    : computedStyle.backgroundImage) ||
                computedStyle.backgroundColor ||
                DEFAULT_CUSTOM_FILL_COLOR,
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
                        enabledTabs:
                            colorStateRef === "customFillColorState"
                                ? ["solid", "custom", "gradient"]
                                : ["solid", "custom"],
                        getUsedCustomColors: () => [],
                        colorPrefix: "",
                        themeColorPrefix: "hb-cp-",
                        applyColor: (colorValue) => {
                            this[colorStateRef].selectedColor = colorValue;
                            this[resetValueRef] = colorValue;
                        },
                        applyColorPreview: (colorValue) => {
                            this[colorStateRef].selectedColor = colorValue;
                            this.onChange();
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
        if (!this.state.editing) {
            this.loadAsyncLinkPreview();
        }
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
            this.onClickApply();
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

    onClickNewWindow(checked) {
        this.state.linkTarget = checked ? "_blank" : "";
    }

    onClickStripDomain(checked) {
        this.state.stripDomain = checked;
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
    getButtonShape() {
        const shapeToRegex = (shape) => {
            const parts = shape.trim().split(/\s+/);
            const regexParts = parts.map((cls) => {
                if (["outline", "fill"].includes(cls)) {
                    cls = `btn-${cls}`;
                }
                return `(?=.*\\b${cls}\\b)`;
            });
            return { regex: new RegExp(regexParts.join("")), nbParts: parts.length };
        };
        // If multiple shapes match, prefer the one with more specificity.
        let shapeMatched = "";
        let matchScore = 0;
        for (const { shape } of this.buttonShapeData) {
            if (!shape) {
                continue;
            }
            const { regex, nbParts } = shapeToRegex(shape);
            if (regex.test(this.props.linkElement.className)) {
                if (matchScore < nbParts) {
                    matchScore = nbParts;
                    shapeMatched = shape;
                }
            }
        }
        return shapeMatched;
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
        }
    }

    get classes() {
        let classes = [...this.props.linkElement.classList]
            .filter(
                (value) =>
                    !value.match(/^(btn.*|rounded-circle|flat|(text|bg)-(o-color-\d$|\d{3}$))$/)
            )
            .join(" ");

        let stylePrefix = "";
        if (this.state.type === "custom") {
            if (this.state.buttonSize) {
                classes += ` btn-${this.state.buttonSize}`;
            }
            if (this.state.buttonShape) {
                const buttonShape = this.state.buttonShape.split(" ");
                if (["outline", "fill"].includes(buttonShape[0])) {
                    stylePrefix = `${buttonShape[0]}-`;
                }
                classes += ` ${buttonShape.slice(stylePrefix ? 1 : 0).join(" ")}`;
            }
        }
        if (this.state.type) {
            classes += ` btn btn-${stylePrefix}${this.state.type}`;
        }

        const textColor = this.customTextColorState.selectedColor;
        if (isCSSVariable(textColor)) {
            classes += " text-" + textColor;
        }

        const fillColor = this.customFillColorState.selectedColor;
        if (isCSSVariable(fillColor)) {
            classes += " bg-" + fillColor;
        }

        return classes.trim();
    }

    get customStyles() {
        if (!this.props.allowCustomStyle || this.state.type !== "custom") {
            return false;
        }
        let customStyles = "";

        const textColor = this.customTextColorState.selectedColor;
        if (!isCSSVariable(textColor)) {
            customStyles += `color: ${textColor}; `;
        }

        const fillColor = this.customFillColorState.selectedColor;
        if (!isCSSVariable(fillColor)) {
            const backgroundProperty = fillColor.includes("gradient")
                ? "background-image"
                : "background-color";
            customStyles += `${backgroundProperty}: ${fillColor}; `;
        }

        const borderColor = this.customBorderColorState.selectedColor;
        customStyles += `border-width: ${this.state.customBorderSize}px; `;
        customStyles += `border-color: ${formatColor(borderColor)}; `;
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
    /**
     * Checks if the given URL is using the domain where the content being
     * edited is reachable, i.e. if this URL should be stripped of its domain
     * part and converted to a relative URL if put as a link in the content.
     *
     * @private
     * @returns {boolean}
     */
    isAbsoluteURLInCurrentDomain() {
        // First check if it is a relative URL: if it is, we don't want to check
        // further as we will always leave those untouched.
        let hasProtocol;
        try {
            hasProtocol = !!new URL(this.state.url).protocol;
        } catch {
            hasProtocol = false;
        }
        if (!hasProtocol) {
            return false;
        }

        const urlObj = new URL(this.state.url, window.location.origin);
        // Chosen heuristic to detect someone trying to enter a link using
        // its Odoo instance domain. We just suppose it should be a relative
        // URL (if unexpected behavior, the user can just not enter its Odoo
        // instance domain but its real domain, or opt-out from the domain
        // stripping). Mentioning an .odoo.com domain, especially its own
        // one, is always a bad practice anyway.
        return (
            urlObj.origin === window.location.origin ||
            new RegExp(`^https?://${session.db}\\.odoo\\.com(/.*)?$`).test(urlObj.origin)
        );
    }
}
