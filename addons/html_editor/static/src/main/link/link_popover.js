import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { cleanZWChars, deduceURLfromText } from "./utils";

export class LinkPopover extends Component {
    static template = "html_editor.linkPopover";
    static props = {
        linkEl: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        onApply: Function,
        onRemove: Function,
        onCopy: Function,
        onClose: Function,
        getInternalMetaData: Function,
        getExternalMetaData: Function,
        getAttachmentMetadata: Function,
        isImage: Boolean,
        LinkPopoverState: Object,
        type: String,
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
    buttonSizesData = [
        { size: "sm", label: _t("Small") },
        { size: "", label: _t("Medium") },
        { size: "lg", label: _t("Large") },
    ];
    buttonStylesData = [
        { style: "fill", label: _t("Fill") },
        { style: "fill,rounded-circle", label: _t("Fill + Rounded") },
        { style: "outline", label: _t("Outline") },
        { style: "outline,rounded-circle", label: _t("Outline + Rounded") },
    ];
    setup() {
        this.ui = useService("ui");
        this.notificationService = useService("notification");
        this.uploadService = useService("uploadLocalFiles");

        this.state = useState({
            editing: this.props.LinkPopoverState.editing,
            url: this.props.linkEl.href || "",
            label: cleanZWChars(this.props.linkEl.textContent),
            previewIcon: {
                /** @type {'fa'|'imgSrc'|'mimetype'} */
                type: "fa",
                value: "fa-globe",
            },
            urlTitle: "",
            urlDescription: "",
            linkPreviewName: "",
            imgSrc: "",
            iconSrc: "",
            classes:
                this.props.type === "primary"
                    ? "btn btn-primary"
                    : this.props.linkEl.className || "",
            type:
                this.props.type ||
                this.props.linkEl.className.match(/btn(-[a-z0-9_-]*)(primary|secondary)/)?.pop() ||
                "",
            buttonSize: this.props.linkEl.className.match(/btn-(sm|lg)/)?.[1] || "",
            buttonStyle: this.initButtonStyle(this.props.linkEl.className),
            isImage: this.props.isImage,
            showLabel: !this.props.linkEl.childElementCount,
        });

        this.editingWrapper = useRef("editing-wrapper");
        useAutofocus({
            refName: this.state.isImage || this.state.label !== "" ? "url" : "label",
            mobile: true,
        });
        onMounted(() => {
            if (!this.state.editing) {
                this.loadAsyncLinkPreview();
            }
        });
    }
    initButtonStyle(className) {
        const styleArray = [
            className.match(/btn-([a-z0-9_]+)-(primary|secondary)/)?.[1],
            className.match(/rounded-circle/)?.pop(),
        ];
        return styleArray.every(Boolean)
            ? styleArray.join(",")
            : styleArray.join("") || className.match(/flat/)?.pop() || "";
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
        this.props.onApply(
            this.state.url,
            this.state.label,
            this.state.classes,
            this.state.attachmentId
        );
    }
    onClickEdit() {
        this.state.editing = true;
        this.state.url = this.props.linkEl.href;
        this.state.label = cleanZWChars(this.props.linkEl.textContent);
    }
    async onClickCopy(ev) {
        ev.preventDefault();
        await browser.navigator.clipboard.writeText(this.props.linkEl.href || "");
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
        if (ev.key === "Enter" && !isAutoCompleteDropdownOpen) {
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
            url = "http://" + url;
        }
        return url;
    }
    deduceUrl(text) {
        text = text.trim();
        if (/^(https?:|mailto:|tel:)/.test(text)) {
            // Text begins with a known protocol, accept it as valid URL.
            return text;
        } else {
            return deduceURLfromText(text, this.props.linkEl) || "";
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
            url = new URL(this.state.url); // relative to absolute
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
                .getInternalMetaData(this.state.url)
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

    /**
     * link style preview in editing mode
     */
    onChangeClasses() {
        const shapes = this.state.buttonStyle ? this.state.buttonStyle.split(",") : [];
        const style = ["outline", "fill"].includes(shapes[0]) ? `${shapes[0]}-` : "fill-";
        const shapeClasses = shapes.slice(style ? 1 : 0).join(" ");
        this.state.classes =
            (this.state.type ? `btn btn-${style}${this.state.type}` : "") +
            (this.state.type && shapeClasses ? ` ${shapeClasses}` : "") +
            (this.state.type && this.state.buttonSize ? " btn-" + this.state.buttonSize : "");
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
    }

    isAttachmentUrl() {
        return !!this.state.url.match(/\/web\/content\/\d+/);
    }
}
