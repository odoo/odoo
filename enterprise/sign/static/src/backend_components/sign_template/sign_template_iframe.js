/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";
import { shallowEqual } from "@web/core/utils/arrays";
import { normalizePosition, startResize, generateRandomId } from "@sign/components/sign_request/utils";
import { SignItemCustomPopover } from "@sign/backend_components/sign_template/sign_item_custom_popover";
import { PDFIframe } from "@sign/components/sign_request/PDF_iframe";
import { EditablePDFIframeMixin } from "@sign/backend_components/editable_pdf_iframe_mixin";
import { user } from "@web/core/user";
import { Deferred } from "@web/core/utils/concurrency";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class SignTemplateIframe extends EditablePDFIframeMixin(PDFIframe) {
    /**
     * Renders custom elements inside the PDF.js iframe
     * @param {HTMLIFrameElement} iframe
     * @param {Document} root
     * @param {Object} env
     * @param {Object} owlServices
     * @param {Object} props
     */
    constructor(root, env, owlServices, props) {
        super(root, env, owlServices, props);
        this.deletedSignItemIds = [];
        this.currentRole = this.props.signRoles[0].id;
        this.closePopoverFns = {};
        this.signItemTypesById = this.props.signItemTypes.reduce((obj, type) => {
            obj[type.id] = type;
            return obj;
        }, {});
        this.signRolesById = this.props.signRoles.reduce((obj, role) => {
            obj[role.id] = role;
            return obj;
        }, {});
        this.selectionOptionsById = this.props.signItemOptions.reduce((obj, option) => {
            obj[option.id] = option;
            return obj;
        }, {});
        /**
         * This is used to keep track of the sign items that are currently being
         * fetched from the server. This is used to ensure that the sign item
         * on which a click event is triggered is completely loaded before
         */
        this.negativeIds = {};
        this.radioSets = this.props.radioSets;
    }

    get allowEdit() {
        return !this.props.hasSignRequests;
    }

    renderSidebar() {
        super.renderSidebar();
        if (this.allowEdit && !isMobileOS()) {
            const sideBar = renderToString("sign.signItemTypesSidebar", {
                signItemTypes: this.props.signItemTypes,
            });
            this.root.body.insertAdjacentHTML("afterbegin", sideBar);
        }
    }

    /**
     * Draws the connecting lines between two sign items. Uses `canvas_layer_0` for rendering.
     * @param {SignItem} signItem1 
     * @param {SignItem} signItem2 
     */
    renderConnectingLine(signItem1, signItem2){
        /**
         * For each sign item we have its coordinates inside the corresponding page.
         * In order to allow for lines that cover multiple pages we calculate the (x, y) coordinates 
         * with respect to the entire document.
         * 
            -----------------------------------------
            |           |                           |
            |   --------|----------------------     |
            |   |       y                     |     |
            |   |       |                     |     |
            |____x______-----                 |     |
            |   |       |   |                 |     |
            |   |       -----                 |     |
            |   |         |                   |     |
            |   |       -----                 |     |
            |   |       |   |                 |     |
            |   |       -----                 |     |
            |   |         |                   |     |
            |   |         |         -----     |     |
            |   |          ---------|   |     |     |
            |   |                   -----     |     |
            |   |                             |     |
            |   -------------------------------     |
            |                                       |
            -----------------------------------------

            To connect two items we do the following:
                1. Check if we can connect them with one line (horizontal/verical)
                2. If not, this means that the second item lies in of four quarters with respect to the first item.
                   Check in which quarter does it lie and draw the two lines accordingly.

                            |               |
                      (1)   |               |   (2)
                ------------|----------------------------
                            |               |
                            |  first item   |
                            |               |
                -----------------------------------------
                            |               |
                      (3)   |               |     (4)
                            |               |
         */

        const page1 = this.getPageContainer(signItem1.data.page);
        const page2 = this.getPageContainer(signItem2.data.page);
        const dx1 = page1.offsetLeft + page1.clientLeft;
        const dy1 = page1.offsetTop + page1.clientTop;
        const dx2 = page2.offsetLeft + page2.clientLeft;
        const dy2 = page2.offsetTop + page2.clientTop;
        const x1 = signItem1.data.posX * page1.clientWidth + dx1;
        const y1 = signItem1.data.posY * page1.clientHeight + dy1;
        const w1 = signItem1.data.width * page1.clientWidth;
        const h1 = signItem1.data.height * page1.clientHeight;
        const c1 = {x : x1 + w1 / 2, y: y1 + h1 / 2};
        const x2 = signItem2.data.posX * page2.clientWidth + dx2;
        const y2 = signItem2.data.posY * page2.clientHeight + dy2;
        const w2 = signItem2.data.width * page2.clientWidth;
        const h2 = signItem2.data.height * page2.clientHeight;
        const c2 = {x: x2 + w2 / 2, y: y2 + h2 / 2};
        
        if (!(x2 > x1 + w1 || x1 > x2 + w2)) {
            //One vertical line
            let midx = (Math.max(x1, x2) + Math.min(x1 + w1, x2 + w2)) / 2;
            if(y1 > y2){
                this.renderLine({
                    start: {
                        x: midx,
                        y: y2 + h2,
                    },
                    end: {
                        x: midx,
                        y: y1,
                    }
                });
            } else {
                this.renderLine({
                    start: {
                        x: midx,
                        y: y1 + h1,
                    },
                    end: {
                        x: midx,
                        y: y2,
                    }
                });
            }
        }
        else if (!(y2 > y1 + h1 || y1 > y2 + h2)) {
            //One horizontal line
            let midy = (Math.max(y1, y2) + Math.min(y1 + h1, y2 + h2)) / 2;
            if(x1 > x2){
                this.renderLine({
                    start: {
                        x: x2 + w2,
                        y: midy,
                    },
                    end: {
                        x: x1,
                        y: midy,
                    }
                });
            } else {
                this.renderLine({
                    start: {
                        x: x1 + w1,
                        y: midy,
                    },
                    end: {
                        x: x2,
                        y: midy,
                    }
                });
            }
        } else {
            //we need two lines to connect them
            if (y2 + h2 < y1 && x2 + w2 < x1) {
                //Quarter (1)
                const corner = {
                    x: c2.x,
                    y: c1.y,
                }
                this.renderLine({
                    start: {
                        x: x1,
                        y: c1.y,
                    },
                    end: corner
                });
                this.renderLine({
                    start: corner,
                    end:{
                        x: c2.x,
                        y: y2 + h2,
                    }
                });
            } else if (y2 + h2 < y1 && x2 > x1 + w1) {
                //Quarter (2)
                const corner = {
                    x: c2.x,
                    y: c1.y
                }
                this.renderLine({
                    start: corner,
                    end:{
                        x: x1 + w1,
                        y: c1.y
                    }
                });
                this.renderLine({
                    start: corner,
                    end:{
                        x: c2.x,
                        y: y2 + h2,
                    }
                });
            } else if (y2 > y1 + h1 && x2 + w2 < x1) {
                //Quarter (3)
                const corner = {
                    x: c1.x,
                    y: c2.y
                }
                this.renderLine({
                    start: corner,
                    end: {
                        x: c1.x,
                        y: y1 + h1,
                    }
                });
                this.renderLine({
                    start: corner,
                    end: {
                        x: x2 + w2,
                        y: c2.y
                    }
                });
            } else if (y2 > y1 + h1 && x2 > x1 + w1) {
                //Quarter (4)
                const corner = {
                    x: c1.x,
                    y: c2.y
                }
                this.renderLine({
                    start: corner,
                    end: {
                        x: c1.x,
                        y: y1 + h1,
                    }
                });
                this.renderLine({
                    start: corner,
                    end: {
                        x: x2,
                        y: c2.y
                    }
                });
            }
        }
    }

    /**
     * Draws a dashed line that goes from (data.start.x, data.start.y) to (data.end.x, data.end.y)
     * @param {Object} data
     */
    renderLine(data){
        const canvas = this.getCanvas();
        const ctx = canvas.getContext('2d');
        const scale = this.getCanvasScale();
        ctx.lineWidth = 3 / scale;
        ctx.setLineDash([15 / scale, 7 / scale]);
        ctx.strokeStyle = "orange";
        ctx.beginPath();
        ctx.moveTo(data.start.x / scale, data.start.y / scale);
        ctx.lineTo(data.end.x / scale, data.end.y / scale);
        ctx.stroke();
    }

    /**
     * Renders connecting lines between sign items of type "radio"
     */
    renderAllConnectingLines() {
        const canvas = this.getCanvas();
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }

        for (const radio_set_id in this.radioSets) {
            this.radioSets[radio_set_id].radio_item_ids = this.radioSets[radio_set_id].radio_item_ids.sort((id1, id2) => {
                const data1 = this.getSignItemById(id1).data;
                const data2 = this.getSignItemById(id2).data;
                return (
                    100 * (data1.page - data2.page) +
                    10 * (data1.posY - data2.posY) +
                    (data1.posX - data2.posX)
                );
            });
            for (let i = 1; i < this.radioSets[radio_set_id].radio_item_ids.length; i++) {
                const item1 = this.getSignItemById(this.radioSets[radio_set_id].radio_item_ids[i - 1]);
                const item2 = this.getSignItemById(this.radioSets[radio_set_id].radio_item_ids[i]);
                this.renderConnectingLine(item1, item2);
            }
        }
    }

    registerDragEventsForSignItem(signItem) {
        super.registerDragEventsForSignItem(signItem);
        const display = signItem.el.querySelector(".o_sign_item_display");
        display.addEventListener("click", () => this.openSignItemPopup(signItem));
    }

    /**
     * Handles opening and closing of popovers in template edition
     * @param {SignItem} signItem
     */
    async openSignItemPopup(signItem) {
        const shouldOpenNewPopover = !(signItem.data.id in this.closePopoverFns);
        this.closePopover();
        if (shouldOpenNewPopover) {
            if (signItem.data.id in this.negativeIds) {
                await this.negativeIds[signItem.data.id];
            }
            const header_title = signItem.data.type === "radio" ? "Radio Button" : signItem.data.type_id?.[1] || signItem.data.name;
            const closeFn = this.popover.add(
                signItem.el,
                SignItemCustomPopover,
                {
                    debug: this.env.debug,
                    responsible: signItem.data.responsible,
                    roles: this.signRolesById,
                    alignment: signItem.data.alignment,
                    required: signItem.data.required,
                    header_title: header_title,
                    placeholder: signItem.data.placeholder,
                    id: signItem.data.id,
                    type: signItem.data.type,
                    option_ids: signItem.data.option_ids,
                    num_options: this.getSignItemById(signItem.data.id).data.num_options,
                    radio_set_id: signItem.data.radio_set_id,
                    onValidate: (data) => {
                        this.updateSignItem(signItem, data);
                        this.closePopover();
                    },
                    onDelete: () => {
                        this.closePopover();
                        this.deleteSignItem(signItem);
                    },
                    onClose: () => {
                        this.closePopover();
                    },
                    updateSelectionOptions: (ids) => this.updateSelectionOptions(ids),
                    updateRoles: (id) => this.updateRoles(id),
                },
                {
                    position: "right",
                    onClose: () => {
                        this.closePopoverFns = {};
                    },
                    closeOnClickAway: (target) => !target.closest(".modal"),
                    popoverClass: "sign-popover",
                }
            );
            this.closePopoverFns[signItem.data.id] = {
                close: closeFn,
                signItem,
            };
        }
    }

    /**
     * Closes all open popovers
     */
    closePopover() {
        if (Object.keys(this.closePopoverFns)) {
            for (const id in this.closePopoverFns) {
                this.closePopoverFns[id].close();
            }
            this.closePopoverFns = {};
        }
    }

    /**
     * Updates the radio set, re-renders it and saves the template in case there were changes.
     * @param {Number} sign_item_id
     * @param {Object} data
     */
    async updateRadioButton(sign_item_id, data) {
        const signItem = this.getSignItemById(sign_item_id);
        const { radio_set_id, num_options, responsible, required, placeholder } = signItem.data;
        if (num_options != data.num_options){
            await this.updateRadioNumOptions(radio_set_id, Number(data.num_options));
        }
        let changes = {};
        if (responsible != data.responsible) {
            changes['responsible'] = Number(data.responsible);
        }
        if (required != data.required) {
            changes['required'] = data.required;
        }
        if (placeholder != data.placeholder) {
            changes['placeholder'] = data.placeholder;
        }
        this.updateRadioSet(radio_set_id, changes);
    }

    /**
     * Updates the sign item, re-renders it and saves the template in case there were changes
     * @param {SignItem} signItem
     * @param {Object} data
     */
    updateSignItem(signItem, data) {
        if(signItem.data.type == "radio"){
            return this.updateRadioButton(signItem.data.id, data);
        }
        const changes = Object.keys(data).reduce((changes, key) => {
            if (key in signItem.data) {
                if (Array.isArray(data[key])) {
                    if (!shallowEqual(signItem.data[key], data[key])) {
                        changes[key] = data[key];
                    }
                } else if (signItem.data[key] !== data[key]) {
                    changes[key] = data[key];
                }
            }
            return changes;
        }, {});

        if (Object.keys(changes).length) {
            const pageNumber = signItem.data.page;
            const page = this.getPageContainer(pageNumber);
            signItem.el.parentElement.removeChild(signItem.el);
            const newData = {
                ...signItem.data,
                ...changes,
                updated: true,
            };
            this.signItems[pageNumber][newData.id] = {
                data: newData,
                el: this.renderSignItem(newData, page),
            };
            this.refreshSignItems();
            this.currentRole = newData.responsible;
            this.saveChanges();
        }
    }

    /**
     * Deletes a radio set from the template
     * @param {radio_set_id}
     */
    deleteRadioSet(radio_set_id) {
        const radioSet = this.radioSets[radio_set_id];
        radioSet.radio_item_ids.forEach((id) => {
            const signItem = this.getSignItemById(id);
            signItem.el.parentElement.removeChild(signItem.el);
            delete this.signItems[signItem.data.page][id];
        })
        delete this.radioSets[radio_set_id];
        this.renderAllConnectingLines();
        this.orm.unlink('sign.item.radio.set', [radio_set_id]);
    }

    /**
     * Deletes a sign item from the template
     * @param {SignItem} signItem
     */
    deleteSignItem(signItem) {
        if (signItem.data.type == "radio"){
            return this.deleteRadioSet(this.getSignItemById(signItem.data.id).data.radio_set_id);
        }
        this.deletedSignItemIds.push(signItem.data.id);
        super.deleteSignItem(signItem);
    }

    /**
     * Enables resizing and drag/drop for sign items
     * @param {SignItem} signItem
     */
    enableCustom(signItem) {
        if (this.allowEdit) {
            startResize(signItem, this.onResizeItem.bind(this));
            this.registerDragEventsForSignItem(signItem);
        }
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
        const responsible = signItem.responsible ?? (signItem.responsible_id?.[0] || 0);
        const type = this.signItemTypesById[signItem.type_id[0]].item_type;
        if (type === "selection") {
            const options = signItem.option_ids.map((id) => this.selectionOptionsById[id]);
            signItem.options = options;
        }
        return Object.assign(signItem, {
            readonly: true,
            editMode: true,
            required: Boolean(signItem.required),
            responsible,
            type,
            placeholder: signItem.placeholder || signItem.name || "",
            responsibleName: this.signRolesById[responsible].name,
            classes: `o_color_responsible_${this.signRolesById[responsible].color} o_readonly_mode`,
            style: `top: ${normalizedPosY * 100}%; left: ${normalizedPosX * 100}%;
                    width: ${signItem.width * 100}%; height: ${signItem.height * 100}%;
                    text-align: ${signItem.alignment}`,
        });
    }

    /**
     * Hook executed before rendering the sign items and the sidebar
     */
    preRender() {
        super.preRender();
        if (this.allowEdit && !isMobileOS()) {
            const outerContainer = this.root.querySelector("#outerContainer");
            Object.assign(outerContainer.style, {
                width: "auto",
                marginLeft: "14rem",
            });
            outerContainer.classList.add("o_sign_field_type_toolbar_visible");
            this.root.dispatchEvent(new Event("resize"));
        } else if (!this.allowEdit) {
            const div = this.root.createElement("div");
            Object.assign(div.style, {
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                zIndex: 110,
                opacity: 0.75,
            });
            this.root.querySelector("#viewer").style.position = "relative";
            this.root.querySelector("#viewer").prepend(div);
        }
        this.insertRotatePDFButton();
    }

    insertRotatePDFButton() {
        const printButton = this.root.querySelector("#printButton");
        const button = this.root.createElement("button");
        button.setAttribute("id", "pageRotateCw");
        button.className = "toolbarButton o_sign_rotate rotateCw";
        button.title = _t("Rotate Clockwise");
        printButton.parentNode.insertBefore(button, printButton);
        button.addEventListener("click", (e) => this.rotatePDF(e));
    }

    postRender() {
        super.postRender();
        if (this.allowEdit) {
            const viewerContainer = this.root.querySelector("#viewerContainer");
            // close popover when clicking outside of a sign item
            viewerContainer.addEventListener(
                "click",
                (e) => {
                    if (!e.target.closest(".o_sign_item_display")) {
                        this.closePopover();
                    }
                },
                { capture: true }
            );
            this.root.addEventListener("keyup", (e) => this.handleKeyUp(e));
        }
    }

    handleKeyUp(e) {
        if (e.key === "Delete" && Object.keys(this.closePopoverFns)) {
            //delete any element that has its popover open
            for (const id in this.closePopoverFns) {
                const { close, signItem } = this.closePopoverFns[id];
                typeof close === "function" && close();
                this.deleteSignItem(signItem);
            }
            this.closePopoverFns = {};
        }
    }

    async saveChanges() {
        const items = this.signItems;
        for (const page in items) {
            for (const id in items[page]) {
                const signItem = items[page][id].data;
                if (signItem.id < 0) {
                    this.negativeIds[id] = new Deferred();
                }
            }
        }
        let new_radio_items = []
        const Id2UpdatedItem = await this.props.saveTemplate();
        Object.entries(Id2UpdatedItem).forEach(([previousId, { page, id }]) => {
            if (Number(previousId) !== id && this.signItems[page][previousId]) {
                const prevEl = this.signItems[page][previousId].el;
                const prevData = this.signItems[page][previousId].data;
                this.signItems[page][id] = {
                    data: prevData,
                    el: prevEl,
                };
                this.negativeIds[previousId]?.resolve();
                delete this.negativeIds[previousId];
                delete this.signItems[page][previousId];
                this.signItems[page][id].el.dataset.id = id;
                if (prevData.type == "radio") {
                    new_radio_items.push({'page': page,'id': id});
                }
            }
            this.signItems[page][id].data.updated = false;
        });
        // Assign the radio_set info to the newely created radio items
        if (new_radio_items.length) {
            const info = await this.props.getRadioSetInfo(new_radio_items.map((obj) => obj.id));
            new_radio_items.forEach(({page, id}) => {
                const { data, el } = this.signItems[page][id];
                const updatedData = Object.assign({}, data, info[id]);
                const {radio_set_id, num_options} = info[id];
                if (!this.radioSets[radio_set_id]) {
                    this.radioSets[radio_set_id] = {
                        num_options: 0,
                        radio_item_ids: [],
                    }
                }
                this.radioSets[radio_set_id].num_options = num_options;
                this.radioSets[radio_set_id].radio_item_ids.push(id);
                this.signItems[page] = {
                  ...this.signItems[page],
                  [id]: {
                    data: updatedData,
                    el: el,
                  },
                };
            });
        }
        this.deletedSignItemIds = [];
        this.renderAllConnectingLines();
    }

    /**
     * @typedef {Object} SignItem
     * @property {Object} data // sign item data returned from the search_read
     * @property {HTMLElement} el // html element of the sign item
     */

    /**
     * Updates the local selection options to include the new records
     * @param {Array<Number>} optionIds
     */
    async updateSelectionOptions(optionIds) {
        const newIds = optionIds.filter((id) => !(id in this.selectionOptionsById));
        const newOptions = await this.orm.searchRead(
            "sign.item.option",
            [["id", "in", newIds]],
            ["id", "value"],
            { context: user.context }
        );
        for (const option of newOptions) {
            this.selectionOptionsById[option.id] = option;
        }
    }

    /**
     * Creates #count new sign radio items and chains them vertically to the lastSignItem
     * by increasing of Y position, renders them and saves the template.
     * @param {SignItem} lastSignItem
     * @param {Number} count
     */
    async render_new_radio_items(lastSignItem, count) {
        let tail = lastSignItem;
        for(let i = 0; i < count; i++){
            const new_id = generateRandomId();
            const new_data = { ...tail.data };
            new_data['id'] = new_id;
            new_data['posY'] += 0.025;
            this.signItems[new_data.page][new_id] = {
                data: new_data,
                el: this.renderSignItem(new_data, this.getPageContainer(new_data.page)),
            }
            tail = this.signItems[new_data.page][new_id];
            new_data.updated = true;
        }
        this.refreshSignItems();
        await this.saveChanges();
    }

    /**
     * Removes the last #count sign items from radio_item_ids from the template and saves the changes.
     * @param {Number[]} radio_item_ids
     * @param {Number} count
     */
    async deleteRadioItems(radio_item_ids, count) {
        let deleted_sign_items = [];
        for (let i = 0; i < count; i++) {
            const id = radio_item_ids[radio_item_ids.length - 1 - i];
            const signItem = this.getSignItemById(id);
            deleted_sign_items.push(signItem);
        }
        await this.deleteSignItems(deleted_sign_items);
    }

    /**
     * Apply changes to the entire radio set, re-renders sign items and saved the changes.
     * @param {Number} radio_set_id
     * @param {Object} changes
     * @returns 
     */
    async updateRadioSet(radio_set_id, changes) {
        if(Object.keys(changes).length === 0) {
            return;
        }
        const radio_set = this.radioSets[radio_set_id];
        radio_set.radio_item_ids.forEach((id) => {
            const signItem = this.getSignItemById(id);
            const pageNumber = signItem.data.page;
            const page = this.getPageContainer(pageNumber);
            signItem.el.parentElement.removeChild(signItem.el);
            const newData = {
                ...signItem.data,
                ...changes,
                updated: true,
            };
            this.signItems[pageNumber][id] = {
                data: newData,
                el: this.renderSignItem(newData, page),
            };
        });
        this.refreshSignItems();
        await this.saveChanges();
    }

    /**
     * Changes radio set number of options, renders new items, deletes extra items and saves changes.
     * @param {Number} radio_set_id
     * @param {Number} count
     */
    async updateRadioNumOptions(radio_set_id, count) {
        const radio_set = this.radioSets[radio_set_id];
        if (radio_set.num_options < count) {
            const signItem = this.getSignItemById(radio_set.radio_item_ids[radio_set.num_options - 1]);
            await this.render_new_radio_items(signItem, count - radio_set.num_options);
        }else if (radio_set.num_options > count) {
            await this.deleteRadioItems(radio_set.radio_item_ids, radio_set.num_options - count);
        }
        const new_radio_set = this.radioSets[radio_set_id];
        new_radio_set.radio_item_ids.forEach((id) => {
            const signItem = this.getSignItemById(id);
            signItem.data.num_options = new_radio_set.num_options;
        })
    }

    /**
     * Updates the local roles to include new records
     * @param {Number} id role id
     */
    async updateRoles(id) {
        if (!(id in this.signRolesById)) {
            const newRole = await this.orm.searchRead("sign.item.role", [["id", "=", id]], []);
            this.signRolesById[newRole[0].id] = newRole[0];
        }
    }
}
