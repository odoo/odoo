/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { renderToString } from "@web/core/utils/render";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { normalizePosition, isVisible } from "./utils";

export class PDFIframe {
    /**
     * Renders custom elements inside the PDF.js iframe
     * @param {HTMLIFrameElement} iframe
     * @param {Document} root
     * @param {Object} env
     * @param {Object} owlServices
     * @param {Object} props
     */
    constructor(root, env, owlServices, props) {
        this.root = root;
        this.env = env;
        Object.assign(this, owlServices);
        this.props = props;
        this.cleanupFns = [];

        this.readonly = props.readonly;
        this.signItemTypesById = this.props.signItemTypes.reduce((obj, type) => {
            obj[type.id] = type;
            return obj;
        }, {});
        this.selectionOptionsById = this.props.signItemOptions.reduce((obj, option) => {
            obj[option.id] = option;
            return obj;
        }, {});
        this.radioSets = this.props.radioSets;
        if (this.root) {
            this.waitForPagesToLoad();
        }
    }

    waitForPagesToLoad() {
        const errorElement = this.root.querySelector("#errorMessage");
        if (isVisible(errorElement)) {
            return this.dialog.add(AlertDialog, {
                body: _t("Need a valid PDF to add signature fields!"),
            });
        }
        this.pageCount = this.root.querySelectorAll(".page").length;
        if (this.pageCount > 0) {
            this.start();
        } else {
            setTimeout(() => this.waitForPagesToLoad(), 50);
        }
    }

    start() {
        this.signItems = this.getSignItems();
        this.loadCustomCSS().then(() => {
            this.pageCount = this.root.querySelectorAll(".page").length;
            this.clearNativePDFViewerButtons();
            this.startPinchService();
            this.preRender();
            this.renderSidebar();
            this.addCanvasLayer();
            this.renderSignItems();
            this.postRender();
        });
    }

    unmount() {
        this.cleanupFns.forEach((fn) => typeof fn === "function" && fn());
    }

    async loadCustomCSS() {
        const assets = await rpc("/sign/render_assets_pdf_iframe", {
            args: [{ debug: this.env.debug }],
        });
        this.root.querySelector("head").insertAdjacentHTML("beforeend", assets);
    }

    clearNativePDFViewerButtons() {
        const selectors = [
            "#pageRotateCw",
            "#pageRotateCcw",
            "#openFile",
            "#presentationMode",
            "#viewBookmark",
            "#printButton",
            "#downloadButton",
            "#secondaryOpenFile",
            "#secondaryPresentationMode",
            "#secondaryViewBookmark",
            "#secondaryPrint",
            "#secondaryDownload",
        ];
        const elements = this.root.querySelectorAll(selectors.join(", "));
        elements.forEach((element) => {
            element.style.display = "none";
        });
        this.root.querySelector("#lastPage").nextElementSibling.style.display = "none";
        // prevent password from being autocompleted in search input
        this.root.querySelector("#findInput").value = "";
        this.root.querySelector("#findInput").setAttribute("autocomplete", "off");
        const passwordInputs = this.root.querySelectorAll("[type=password]");
        Array.from(passwordInputs).forEach((input) =>
            input.setAttribute("autocomplete", "new-password")
        );
    }

    /**
     * Adds canvas layer used to draw connecting lines between radio items.
     */
    addCanvasLayer() {
        const viewer = this.root.querySelector("#viewer");
        const layer = document.createElement("canvas");
        const scale = this.getCanvasScale();
        layer.id = "canvas_layer_0";
        layer.style.position = "absolute";
        layer.style.top = "0";
        layer.style.left = "0";
        layer.style.zIndex = 1;
        layer.style.width = viewer.offsetWidth + "px";
        layer.style.height = viewer.offsetHeight + "px";
        layer.width = viewer.offsetWidth / scale;
        layer.height = viewer.offsetHeight / scale;
        viewer.appendChild(layer);
    }

    /**
     * Used when signing a sign request
     */
    renderSidebar() {}

    renderSignItems() {
        for (const page in this.signItems) {
            const pageContainer = this.getPageContainer(page);
            for (const id in this.signItems[page]) {
                const signItem = this.signItems[page][id];
                signItem.el = this.renderSignItem(signItem.data, pageContainer);
            }
        }
        this.updateFontSize();
        this.renderAllConnectingLines();
    }

    /**
     * Renders connecting lines between radio items.
     */

    renderAllConnectingLines() {}

    /**
     * register sign item events. in template edition, should be overwritten to add drag/drop events
     */
    enableCustom(signItem) {}

    startPinchService() {
        const pinchTarget = this.root.querySelector("#viewerContainer #viewer");
        const handleTouchMove = (e) => {
            if (e.touches.length == 2) {
                // To allow zooming in pdf only.
                e.preventDefault();
            }
        };
        pinchTarget.addEventListener("touchmove", handleTouchMove);
        this.cleanupFns.push(() => {
            pinchTarget.removeEventListener("touchmove", handleTouchMove);
        });
    }

    /**
     * Renders a sign item using its data and attaches it to a target html element
     * @param { Object } signItemData
     * @property
     */
    renderSignItem(signItemData, target) {
        const signItemElement = renderToString("sign.signItem", this.getContext(signItemData));
        target.insertAdjacentHTML("beforeend", signItemElement);
        const signItem = target.lastChild;
        signItem.classList.add("d-none");
        this.enableCustom({ el: signItem, data: signItemData });
        return signItem;
    }

    /**
     * Extends the rendering context of the sign item based on its data
     * @param {SignItem.data} signItem
     * @returns {Object}
     */
    getContext(signItem) {
        const normalizedPosX =
            Math.round(normalizePosition(signItem.posX, signItem.width) * 1000) / 1000;
        const normalizedPosY =
            Math.round(normalizePosition(signItem.posY, signItem.height) * 1000) / 1000;
        const responsible = parseInt(signItem.responsible ?? (signItem.responsible_id?.[0] || 0));
        const type = this.signItemTypesById[signItem.type_id].item_type;
        if (type === "selection") {
            const options = signItem.option_ids.map((id) => this.selectionOptionsById[id]);
            signItem.options = options;
        }
        // handles prefilled values with 0
        if (signItem.value === 0) {
            signItem.value = "0";
        }
        const readonly =
            this.readonly ||
            (responsible > 0 && responsible !== this.currentRole) ||
            !!signItem.value;
        const isCurrentRole = this.currentRole === parseInt(responsible);
        const placeholder =
            signItem.placeholder ||
            (isCurrentRole && signItem.name) ||
            (this.readonly && `${signItem.name}\n${signItem.responsible_name}`) ||
            "";
        return Object.assign(signItem, {
            readonly: signItem.readonly ?? readonly,
            editMode: signItem.editMode ?? false,
            required: Boolean(signItem.required),
            responsible,
            type,
            placeholder: placeholder,
            classes: `
                ${isCurrentRole ? "o_sign_sign_item_default" : ""}
                ${signItem.required && isCurrentRole ? "o_sign_sign_item_required" : ""}
                ${readonly && isCurrentRole ? "o_readonly_mode" : ""}
                ${this.readonly ? "o_sign_sign_item_pdfview" : ""}`,
            style: `top: ${normalizedPosY * 100}%; left: ${normalizedPosX * 100}%;
                    width: ${signItem.width * 100}%; height: ${signItem.height * 100}%;
                    text-align: ${signItem.alignment}`,
        });
    }

    /**
     * PDF.js removes custom elements every once in a while.
     * So we need to constantly re-render them :(
     * We keep the elements stored in memory, so we don't need to call the qweb engine everytime a element is detached
     */
    refreshSignItems() {
        for (const page in this.signItems) {
            const pageContainer = this.getPageContainer(page);
            for (const id in this.signItems[page]) {
                const signItem = this.signItems[page][id].el;
                signItem.classList.remove("d-none");
                if (signItem && signItem.hasAttribute("data-signature")) {
                    signItem.addEventListener("dragstart", (event) => {
                        event.preventDefault();
                    });
                }
                if (!signItem.parentElement || !signItem.parentElement.classList.contains("page")) {
                    pageContainer.append(signItem);
                }
            }
        }
        this.updateFontSize();
        this.renderAllConnectingLines();
    }

    /**
     * Hook executed before rendering the sign items and the sidebar
     */
    preRender() {
        const viewerContainer = this.root.querySelector("#viewerContainer");
        viewerContainer.style.visibility = "visible";
        this.setInitialZoom();
    }

    get normalSize() {
        return this.root.querySelector(".page").clientHeight * 0.015;
    }

    /**
     * Updates the font size of all sign items in case there was a zoom/resize of element
     */
    updateFontSize() {
        for (const page in this.signItems) {
            for (const id in this.signItems[page]) {
                const signItem = this.signItems[page][id];
                this.updateSignItemFontSize(signItem);
            }
        }
    }

    /**
     * Updates the font size of a determined sign item
     * @param {SignItem}
     */
    updateSignItemFontSize({ el, data }) {
        const largerTypes = ["signature", "initial", "textarea", "selection"];
        const size = largerTypes.includes(data.type)
            ? this.normalSize
            : parseFloat(el.clientHeight);
        el.style.fontSize = `${size * 0.8}px`;
    }

    async rotatePDF(e) {
        const button = e.target;
        button.setAttribute("disabled", "");
        const result = await this.props.rotatePDF();
        if (result) {
            this.root.querySelector("#pageRotateCw").click();
            button.removeAttribute("disabled");
            this.refreshSignItems();
        }
    }

    setInitialZoom() {
        let button = this.root.querySelector("button#zoomInButton");
        if (!this.env.isSmall) {
            button = this.root.querySelector("button#zoomOutButton");
            button.click();
        }
        button.click();
    }

    postRender() {
        const refreshSignItemsIntervalId = setInterval(() => this.refreshSignItems(), 1000);
        this.cleanupFns.push(() => clearInterval(refreshSignItemsIntervalId));
    }

    /**
     * Creates rendering context for the sign item based on the sign item type
     * @param {number} typeId
     * @returns {Object} context
     */
    createSignItemDataFromType(typeId) {
        const type = this.signItemTypesById[typeId];
        return {
            required: true,
            editMode: true,
            readonly: true,
            updated: true,
            responsible: this.currentRole,
            option_ids: [],
            options: [],
            name: type.name,
            width: type.default_width,
            height: type.default_height,
            alignment: "center",
            type: type.item_type,
            placeholder: type.placeholder,
            classes: `o_color_responsible_${this.signRolesById[this.currentRole].color}`,
            style: `width: ${type.default_width * 100}%; height: ${type.default_height * 100}%;`,
            type_id: [type.id],
        };
    }

    /**
     * @typedef {Object} SignItem
     * @property {Object} data // sign item data returned from the search_read
     * @property {HTMLElement} el // html element of the sign item
     */

    /**
     * Converts a list of sign items to an object indexed by page and id
     * @returns { Object.<page:number, Object.<id:number, SignItem >>}
     */
    getSignItems() {
        const signItems = {};
        for (let currentPage = 1; currentPage <= this.pageCount; currentPage++) {
            signItems[currentPage] = {};
        }
        for (const signItem of this.props.signItems) {
            signItems[signItem.page][signItem.id] = {
                data: signItem,
                el: null,
            };
        }
        return signItems;
    }

    /**
     * Gets page container from the page number
     * @param {Number} page
     * @returns {HTMLElement} pageContainer
     */
    getPageContainer(page) {
        return this.root.querySelector(`.page[data-page-number="${page}"]`);
    }

    /**
     * @returns canvas layer used for drawing radio item connecting lines.
     */
    getCanvas() {
        return this.root.querySelector("#canvas_layer_0");
    }

    /**
     *
     * @returns scale of the canvas if its height exceeds the maximum size, else 1.
     */
    getCanvasScale() {
        //@see https://developer.mozilla.org/en-US/docs/Web/HTML/Element/canvas#maximum_canvas_size
        const MAX_CANVAS_HEIGHT = 16384;
        const viewer_height = this.root.querySelector("#viewer").offsetHeight;
        return Math.ceil(viewer_height / MAX_CANVAS_HEIGHT);
    }
}
