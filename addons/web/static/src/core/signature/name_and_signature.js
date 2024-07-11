/** @odoo-module **/

import { loadJS } from "@web/core/assets";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { renderToString } from "@web/core/utils/render";
import { getDataURLFromFile } from "@web/core/utils/urls";

import { Component, useState, onWillStart, useRef, useEffect } from "@odoo/owl";

let htmlId = 0;
export class NameAndSignature extends Component {
    setup() {
        this.rpc = useService("rpc");

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
            this.fonts = await this.rpc(`/web/sign/get_fonts/${this.props.defaultFont}`);
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/jSignature/jSignatureCustom.js");
            await loadJS("/web/static/src/libs/jSignatureCustom.js");
        });

        this.signatureRef = useRef("signature");
        useEffect(
            (el) => {
                if (el) {
                    this.$signatureField = $(".o_web_sign_signature");
                    this.$signatureField.on("change", () => {
                        this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
                    });
                    this.jSignature();
                    this.resetSignature();
                    this.props.signature.getSignatureImage = () =>
                        this.jSignature("getData", "image");
                    this.props.signature.resetSignature = () => this.resetSignature();
                    if (this.state.signMode === "auto") {
                        this.drawCurrentName();
                    }
                }
            },
            () => [this.signatureRef.el]
        );
    }

    /**
     * Draws the current name with the current font in the signature field.
     */
    drawCurrentName() {
        const font = this.fonts[this.currentFont];
        const text = this.getCleanedName();
        const canvas = this.signatureRef.el.querySelector("canvas");
        const img = this.getSVGText(font, text, canvas.width, canvas.height);
        this.printImage(img);
    }

    focusName() {
        // Don't focus on mobile
        if (!isMobileOS() && this.signNameInputRef.el) {
            this.signNameInputRef.el.focus();
        }
    }

    /**
     * Returns the given name after cleaning it by removing characters that
     * are not supposed to be used in a signature. If @see signatureType is set
     * to 'initial', returns the first letter of each word, separated by dots.
     *
     * @returns {string} cleaned name
     */
    getCleanedName() {
        const text = this.props.signature.name;
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

    jSignature() {
        return this.$signatureField.jSignature(...arguments);
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
            this.jSignature("reset");
            this.state.loadIsInvalid = true;
            return false;
        }
        this.state.loadIsInvalid = false;

        const result = await getDataURLFromFile(file);
        this.printImage(result);
    }

    onClickSignAutoSelectStyle() {
        this.state.showFontList = true;
    }

    onClickSignDrawClear() {
        this.jSignature("reset");
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
    printImage(imgSrc) {
        const image = new Image();
        image.onload = () => {
            // don't slow down the UI if the drawing is slow, and prevent
            // drawing twice when calling this method in rapid succession
            clearTimeout(this.drawTimeout);
            this.drawTimeout = setTimeout(() => {
                let width = 0;
                let height = 0;
                const ratio = image.width / image.height;

                const signatureEl = this.signatureRef.el;
                if (!signatureEl) {
                    return;
                }
                const canvas = signatureEl.querySelector("canvas");
                const context = canvas.getContext("2d");

                if (image.width / canvas.width > image.height / canvas.height) {
                    width = canvas.width;
                    height = parseInt(width / ratio);
                } else {
                    height = canvas.height;
                    width = parseInt(height * ratio);
                }
                this.jSignature("reset");
                const ignoredContext = pick(context, "shadowOffsetX", "shadowOffsetY");
                Object.assign(context, { shadowOffsetX: 0, shadowOffsetY: 0 });
                context.drawImage(
                    image,
                    0,
                    0,
                    image.width,
                    image.height,
                    (canvas.width - width) / 2,
                    (canvas.height - height) / 2,
                    width,
                    height
                );
                Object.assign(context, ignoredContext);
                this.props.signature.isSignatureEmpty = this.isSignatureEmpty;
                return this.isSignatureEmpty;
            }, 0);
        };
        image.src = imgSrc;
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
        const { width, height } = this.resizeSignature();

        this.$signatureField.empty().jSignature({
            "decor-color": "#D1D0CE",
            "background-color": "rgba(255,255,255,0)",
            "show-stroke": false,
            color: this.props.fontColor,
            lineWidth: 2,
            width: width,
            height: height,
        });
        this.emptySignature = this.jSignature("getData");

        this.setMode(this.state.signMode, true);

        this.focusName();
    }

    resizeSignature() {
        // recompute size based on the current width
        this.signatureRef.el.style.width = "unset";
        const width = this.signatureRef.el.clientWidth;
        const height = parseInt(width / this.props.displaySignatureRatio);

        // necessary because the lib is adding invisible div with margin
        // signature field too tall without this code
        this.state.signature = {
            width,
            height,
        };
        Object.assign(this.signatureRef.el.querySelector("canvas").style, { width, height });
        return { width, height };
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
    async setMode(mode, reset) {
        if (reset !== true && mode === this.signMode) {
            // prevent flickering and unnecessary compute
            return;
        }

        this.state.signMode = mode;

        this.jSignature(this.state.signMode === "draw" ? "enable" : "disable");
        this.jSignature("reset");

        if (this.state.signMode === "auto") {
            // draw based on name
            this.drawCurrentName();
        }
    }

    /**
     * Returns whether the drawing area is currently empty.
     *
     * @returns {boolean} Whether the drawing area is currently empty.
     */
    get isSignatureEmpty() {
        const signature = this.jSignature("getData");
        return signature && this.emptySignature ? this.emptySignature === signature : true;
    }

    get loadIsInvalid() {
        return this.state.signMode === "load" && this.state.loadIsInvalid;
    }

    get signatureStyle() {
        const { signature } = this.state;
        return signature ? `width: ${signature.width}px; height: ${signature.height}px` : "";
    }
}

NameAndSignature.template = "web.NameAndSignature";
NameAndSignature.components = { Dropdown, DropdownItem };
NameAndSignature.props = {
    signature: { type: Object },
    defaultFont: { type: String, optional: true },
    displaySignatureRatio: { type: Number, optional: true },
    fontColor: { type: String, optional: true },
    signatureType: { type: String, optional: true },
    noInputName: { type: Boolean, optional: true },
    mode: { type: String, optional: true },
};
NameAndSignature.defaultProps = {
    defaultFont: "",
    displaySignatureRatio: 3.0,
    fontColor: "DarkBlue",
    signatureType: "signature",
    noInputName: false,
};
