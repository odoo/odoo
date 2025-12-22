/* global SignaturePad */

import { loadJS } from "@web/core/assets";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";
import { getDataURLFromFile } from "@web/core/utils/urls";

import { Component, useState, onWillStart, useRef, useEffect } from "@odoo/owl";

let htmlId = 0;
export class NameAndSignature extends Component {
    static template = "web.NameAndSignature";
    static components = { Dropdown, DropdownItem };
    static props = {
        signature: { type: Object },
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

    setup() {
        this.htmlId = htmlId++;
        this.defaultName = this.props.signature.name || "";
        this.currentFont = 0;
        this.drawTimeout = null;

        this.state = useState({
            signMode:
                this.props.mode || (this.props.noInputName && !this.defaultName ? "draw" : "auto"),
            showSignatureArea: !!(this.props.noInputName || this.defaultName),
            showFontList: false,
        });

        this.signNameInputRef = useRef("signNameInput");
        this.signInputLoad = useRef("signInputLoad");
        useAutofocus({ refName: "signNameInput" });
        useEffect(
            (el) => {
                if (el) {
                    el.click();
                }
            },
            () => [this.signInputLoad.el]
        );

        onWillStart(async () => {
            this.fonts = await rpc(`/web/sign/get_fonts/${this.props.defaultFont}`);
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/signature_pad/signature_pad.umd.js");
        });

        this.signatureRef = useRef("signature");
        useEffect(
            (el) => {
                if (el) {
                    this.signaturePad = new SignaturePad(el, {
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
                    this.props.signature.getSignatureImage = () => this.signaturePad.toDataURL();
                    this.props.signature.resetSignature = () => this.resetSignature();
                    if (this.state.signMode === "auto") {
                        this.drawCurrentName();
                    }
                    if (this.props.signature.signatureImage) {
                        this.clear();
                        this.fromDataURL(this.props.signature.signatureImage);
                    }
                }
            },
            () => [this.signatureRef.el]
        );
    }

    /**
     * Draws the current name with the current font in the signature field.
     */
    async drawCurrentName() {
        const font = this.fonts[this.currentFont];
        const text = this.getCleanedName();
        const canvas = this.signatureRef.el;
        const img = this.getSVGText(font, text, canvas.width, canvas.height);
        await this.printImage(img);
    }

    focusName() {
        // Don't focus on mobile
        if (!isMobileOS() && this.signNameInputRef.el) {
            this.signNameInputRef.el.focus();
        }
    }

    /**
     * Clear the signature field.
     */
    clear() {
        this.signaturePad.clear();
        this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
    }

    /**
    * Loads a signature image from a base64 dataURL and updates the empty state.
    */
    async fromDataURL() {
        await this.signaturePad.fromDataURL(...arguments);
        this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
        this.props.onSignatureChange(this.state.signMode);
    }

    /**
     * Returns the given name after cleaning it by removing characters that
     * are not supposed to be used in a signature. If @see signatureType is set
     * to 'initial', returns the first letter of each word, separated by dots.
     *
     * @returns {string} cleaned name
     */
    getCleanedName() {
        // This replaces non-breaking spaces with breaking spaces
        const text = this.props.signature.name.replace(/ /g, " ");
        if (this.props.signatureType === "initial" && text) {
            return (
                text
                    .split(" ")
                    .map(function (w) {
                        return w[0];
                    })
                    .join(".") + "."
            );
        }
        return text;
    }

    /**
     * Gets an SVG matching the given parameters, output compatible with the
     * src attribute of <img/>.
     *
     * @private
     * @param {string} font: base64 encoded font to use
     * @param {string} text: the name to draw
     * @param {number} width: the width of the resulting image in px
     * @param {number} height: the height of the resulting image in px
     * @returns {string} image = mimetype + image data
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

        return "data:image/svg+xml," + encodeURI(svg);
    }

    getSVGTextFont(font) {
        const height = 100;
        const width = parseInt(height * this.props.displaySignatureRatio);
        return this.getSVGText(font, this.getCleanedName(), width, height);
    }

    uploadFile() {
        this.signInputLoad.el?.click();
    }

    /**
     * Handles change on load file input: displays the loaded image if the
     * format is correct, or displays an error otherwise.
     *
     * @see mode 'load'
     * @private
     * @param {Event} ev
     * @return bool|undefined
     */
    async onChangeSignLoadInput(ev) {
        var file = ev.target.files[0];
        if (file === undefined) {
            return false;
        }
        if (file.type.substr(0, 5) !== "image") {
            this.clear();
            this.state.loadIsInvalid = true;
            return false;
        }
        this.state.loadIsInvalid = false;

        const result = await getDataURLFromFile(file);
        await this.printImage(result);
    }

    onClickSignAutoSelectStyle() {
        this.state.showFontList = true;
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

    /**
     * Displays the given image in the signature field.
     * If needed, resizes the image to fit the existing area.
     *
     * @param {string} imgSrc - data of the image to display
     */
    async printImage(imgSrc) {
        this.clear();
        const c = this.signaturePad.canvas;
        const img = new Image();
        img.onload = () => {
            const ctx = c.getContext("2d");
            var ratio = ((img.width / img.height) > (c.width / c.height)) ? c.width / img.width : c.height / img.height;
            ctx.drawImage( 
                img,
                (c.width / 2) - (img.width * ratio / 2),
                (c.height / 2) - (img.height * ratio / 2)
                , img.width * ratio
                , img.height * ratio
            );
            this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
            this.props.onSignatureChange(this.state.signMode);
        };
        img.src = imgSrc;
        this.signaturePad._isEmpty = false;
    }

    /**
     * (Re)initializes the signature area:
     *  - set the correct width and height of the drawing based on the width
     *      of the container and the ratio option
     *  - empty any previous content
     *  - correctly reset the empty state
     *  - call @see setMode with reset
     */
    resetSignature() {
        this.resizeSignature();
        this.clear();
        this.setMode(this.state.signMode, true);
        this.focusName();
    }

    resizeSignature() {
        // recompute size based on the current width
        const width = this.signatureRef.el.clientWidth;
        const height = parseInt(width / this.props.displaySignatureRatio);

        Object.assign(this.signatureRef.el, { width, height });
    }

    /**
     * Changes the signature mode. Toggles the display of the relevant
     * controls and resets the drawing.
     *
     * @param {string} mode - the mode to use. Can be one of the following:
     *  - 'draw': the user draws the signature manually with the mouse
     *  - 'auto': the signature is drawn automatically using a selected font
     *  - 'load': the signature is loaded from an image file
     * @param {boolean} [reset=false] - Set to true to reset the elements
     *  even if the @see mode has not changed. By default nothing happens
     *  if the @see mode is already selected.
     */
    setMode(mode, reset) {
        if (reset !== true && mode === this.signMode) {
            // prevent flickering and unnecessary compute
            return;
        }

        this.state.signMode = mode;
        this.signaturePad[this.state.signMode === "draw" ? "on" : "off"]();
        this.clear();

        if (this.state.signMode === "auto") {
            // draw based on name
            this.drawCurrentName();
        }
        this.props.onSignatureChange(this.state.signMode);
    }

    /**
     * Returns whether the drawing area is currently empty.
     *
     * @returns {boolean} Whether the drawing area is currently empty.
     */
    get isSignatureEmpty() {
        return this.signaturePad.isEmpty();
    }

    get loadIsInvalid() {
        return this.state.signMode === "load" && this.state.loadIsInvalid;
    }
}
