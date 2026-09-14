// @ts-check
/** @odoo-module native */

import {
    Component,
    onWillDestroy,
    onWillStart,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { rpc } from "@web/core/network/rpc";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { uniqueId } from "@web/core/utils/functions";
import { useAutofocus } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";
import { getDataURLFromFile } from "@web/core/utils/urls";

const log = makeLogger("web.components.signature");

/** @type {Map<string, Promise<string[]>>} */
const fontsCache = new Map();

/**
 * @param {string} fontName
 * @returns {Promise<string[]>}
 */
function loadFonts(fontName) {
    if (!fontsCache.has(fontName)) {
        fontsCache.set(
            fontName,
            rpc(`/web/sign/get_fonts/${fontName}`).catch((error) => {
                fontsCache.delete(fontName);
                throw error;
            }),
        );
    }
    return /** @type {Promise<string[]>} */ (fontsCache.get(fontName));
}
export class NameAndSignature extends Component {
    static template = "web.NameAndSignature";
    static components = { Dropdown, DropdownItem };
    static props = {
        signature: {
            type: Object,
            shape: {
                name: { type: [String, { value: null }], optional: true },
                "*": true,
            },
        },
        defaultFont: { type: String, optional: true },
        displaySignatureRatio: { type: Number, optional: true },
        fontColor: { type: String, optional: true },
        signatureType: { type: String, optional: true },
        noInputName: { type: Boolean, optional: true },
        mode: { type: String, optional: true },
        onSignatureChange: { type: Function, optional: true },
    };
    static defaultProps = {
        defaultFont: "",
        displaySignatureRatio: 3.0,
        fontColor: "DarkBlue",
        signatureType: "signature",
        noInputName: false,
        onSignatureChange: () => {},
    };

    /** @type {string} */
    htmlId;
    defaultName = "";
    currentFont = 0;
    hasPaintedImage = false;
    /** @type {string | Promise<string> | null} */
    paintedImageSrc = null;
    /** @type {KeepLast<any>} */
    printImageKeepLast;
    /** @type {{ signMode: string, showSignatureArea: boolean, loadIsInvalid: boolean|undefined }} */
    state;
    /** @type {import("@odoo/owl").Ref<HTMLInputElement>} */
    signNameInputRef;
    /** @type {import("@odoo/owl").Ref<HTMLInputElement>} */
    signInputLoad;
    /** @type {import("@odoo/owl").Ref<HTMLCanvasElement>} */
    signatureRef;
    /** @type {string[]} */
    fonts = [];
    /** @type {any} */
    SignaturePad;
    /** @type {any} */
    signaturePad;
    previewActive = false;

    setup() {
        useLifecycleLog(log);
        this.htmlId = uniqueId();
        this.props.signature.name ??= "";
        this.defaultName = this.props.signature.name;
        this.printImageKeepLast = new KeepLast({ rejectSuperseded: true });
        onWillDestroy(() => this.printImageKeepLast.cancel());

        this.state = useState({
            signMode:
                this.props.mode ||
                (this.props.noInputName && !this.defaultName ? "draw" : "auto"),
            showSignatureArea: !!(this.props.noInputName || this.defaultName),
            /** @type {boolean|undefined} */
            loadIsInvalid: undefined,
        });

        this.signNameInputRef = /** @type {any} */ (useRef("signNameInput"));
        this.signInputLoad = /** @type {any} */ (useRef("signInputLoad"));
        useAutofocus({ refName: "signNameInput" });
        useEffect(
            (el) => {
                if (el) {
                    el.click();
                }
            },
            () => [this.signInputLoad.el],
        );

        onWillStart(async () => {
            this.fonts = await loadFonts(this.props.defaultFont);
        });

        onWillStart(async () => {
            this.SignaturePad = (await import("signature_pad")).default;
        });

        this.signatureRef = /** @type {any} */ (useRef("signature"));
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                const signature = this.props.signature;
                const callerAccessors = {
                    getSignatureImage: signature.getSignatureImage,
                    resetSignature: signature.resetSignature,
                };
                this.signaturePad = new this.SignaturePad(el, {
                    penColor: this.props.fontColor,
                    backgroundColor: "rgba(255,255,255,0)",
                    minWidth: 2,
                    maxWidth: 2,
                });
                this.signaturePad.addEventListener("endStroke", () => {
                    this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
                    this.props.onSignatureChange(this.state.signMode);
                });
                this.resetSignature();
                this.props.signature.getSignatureImage = () =>
                    this.signaturePad.toDataURL();
                this.props.signature.resetSignature = () => this.resetSignature();
                if (this.state.signMode === "auto") {
                    this.drawCurrentName();
                }
                if (this.props.signature.signatureImage) {
                    this.clear();
                    this.fromDataURL(this.props.signature.signatureImage);
                }
                const resizeObserver = new ResizeObserver(() => this.fitSignature());
                resizeObserver.observe(el);
                return () => {
                    resizeObserver.disconnect();
                    this.signaturePad.off();
                    Object.assign(signature, callerAccessors);
                };
            },
            () => [this.signatureRef.el],
        );
    }

    async drawCurrentName() {
        const font = this.fonts[this.currentFont];
        const text = this.getCleanedName();
        if (text.trim() === "") {
            this.clear();
            return;
        }
        const canvas = /** @type {HTMLCanvasElement} */ (this.signatureRef.el);
        const img = this.getSVGText(font, text, canvas.width, canvas.height);
        await this.printImage(img);
    }

    focusName() {
        if (!isMobileOS() && this.signNameInputRef.el) {
            this.signNameInputRef.el.focus();
        }
    }

    clear() {
        this.printImageKeepLast.cancel();
        this.signaturePad.clear();
        this.hasPaintedImage = false;
        this.paintedImageSrc = null;
        this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
    }

    /** @param {string} imgSrc */
    fromDataURL(imgSrc) {
        return this.printImage(imgSrc);
    }

    /** @returns {string} */
    getCleanedName() {
        const text = (this.props.signature.name ?? "").replaceAll("\u00a0", " ");
        if (this.props.signatureType === "initial" && text) {
            const initials = text
                .split(" ")
                .filter(Boolean)
                .map((w) => w[0]);
            return initials.length ? initials.join(".") + "." : "";
        }
        return text;
    }

    /**
     * @private
     * @param {string} font
     * @param {string} text
     * @param {number} width
     * @param {number} height
     * @returns {string}
     */
    getSVGText(font, text, width, height) {
        const svg = renderToString("web.sign_svg_text", {
            width: width,
            height: height,
            font: font,
            text: text,
            type: this.props.signatureType,
            color: this.props.fontColor,
        });

        return "data:image/svg+xml," + encodeURIComponent(svg);
    }

    getSVGTextFont(font) {
        const height = 100;
        const width = Math.trunc(height * this.props.displaySignatureRatio);
        return this.getSVGText(font, this.getCleanedName(), width, height);
    }

    uploadFile() {
        this.signInputLoad.el?.click();
    }

    /**
     * @private
     * @param {Event} ev
     */
    async onChangeSignLoadInput(ev) {
        const inputEl = /** @type {HTMLInputElement} */ (ev.target);
        const file = inputEl.files?.[0];
        inputEl.value = "";
        if (file === undefined) {
            return false;
        }
        if (!file.type.startsWith("image")) {
            this.clear();
            this.state.loadIsInvalid = true;
            return false;
        }
        this.state.loadIsInvalid = false;

        await this.printImage(getDataURLFromFile(file));
    }

    onClickSignDrawClear() {
        this.clear();
        this.props.onSignatureChange(this.state.signMode);
    }

    onClickSignLoad() {
        this.setMode("load");
    }

    onClickSignAuto() {
        this.setMode("auto");
    }

    onInputSignName(ev) {
        this.props.signature.name = ev.target.value;
        if (!this.state.showSignatureArea && this.getCleanedName()) {
            this.state.showSignatureArea = true;
            return;
        }
        if (this.state.signMode === "auto") {
            this.drawCurrentName();
        }
    }

    onSelectFont(index) {
        this.currentFont = index;
        this.drawCurrentName();
    }

    /** @param {string | Promise<string>} imgSrc */
    async printImage(imgSrc) {
        this.clear();
        const c = this.signaturePad.canvas;
        const img = new Image();
        const decode = async () => {
            img.src = await imgSrc;
            await img.decode();
        };
        try {
            await this.printImageKeepLast.add(decode());
        } catch (error) {
            if (error instanceof SupersededError) {
                log.logic("image load discarded");
                return;
            }
            if (this.state.signMode === "load") {
                this.state.loadIsInvalid = true;
            }
            this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
            this.props.onSignatureChange(this.state.signMode);
            return;
        }
        const ctx = c.getContext("2d");
        const ratio =
            img.width / img.height > c.width / c.height
                ? c.width / img.width
                : c.height / img.height;
        ctx.drawImage(
            img,
            c.width / 2 - (img.width * ratio) / 2,
            c.height / 2 - (img.height * ratio) / 2,
            img.width * ratio,
            img.height * ratio,
        );
        this.hasPaintedImage = true;
        this.paintedImageSrc = imgSrc;
        this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
        this.props.onSignatureChange(this.state.signMode);
    }

    resetSignature() {
        this.resizeSignature();
        this.clear();
        this.setMode(this.state.signMode, true);
        this.focusName();
    }

    resizeSignature() {
        const canvas = this.signatureRef.el;
        if (!canvas) {
            return false;
        }
        const width = canvas.clientWidth;
        const height = Math.trunc(width / this.props.displaySignatureRatio);
        if (canvas.width === width && canvas.height === height) {
            return false;
        }
        Object.assign(canvas, { width, height });
        return true;
    }

    fitSignature() {
        const imgSrc = this.paintedImageSrc;
        if (!this.resizeSignature()) {
            return;
        }
        if (this.state.signMode === "auto") {
            this.drawCurrentName();
        } else if (imgSrc) {
            this.printImage(imgSrc);
        } else {
            this.signaturePad.redraw();
            this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
            this.props.onSignatureChange(this.state.signMode);
        }
    }

    /**
     * @param {string} mode
     * @param {boolean} [reset=false]
     */
    setMode(mode, reset) {
        if (reset !== true && mode === this.state.signMode) {
            return;
        }
        log.logic("setMode", () => ({ mode, reset }));

        this.state.signMode = mode;
        this.signaturePad[this.state.signMode === "draw" ? "on" : "off"]();
        this.clear();

        if (this.state.signMode === "auto") {
            this.drawCurrentName();
        }
        this.props.onSignatureChange(this.state.signMode);
    }

    /** @returns {boolean} */
    get isSignatureEmpty() {
        const canvas = this.signaturePad.canvas;
        return (
            !canvas.width ||
            !canvas.height ||
            (!this.hasPaintedImage && this.signaturePad.isEmpty())
        );
    }

    get loadIsInvalid() {
        return this.state.signMode === "load" && this.state.loadIsInvalid;
    }
}
