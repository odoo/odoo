/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";
import { shallowEqual } from "@web/core/utils/arrays";
import { normalizePosition, startResize } from "@sign/components/sign_request/utils";
import { SignItemCustomPopover } from "@sign/backend_components/sign_template/sign_item_custom_popover";
import { PDFIframe } from "@sign/components/sign_request/PDF_iframe";
import { EditablePDFIframeMixin } from "@sign/backend_components/editable_pdf_iframe_mixin";
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
            const closeFn = this.popover.add(
                signItem.el,
                SignItemCustomPopover,
                {
                    debug: this.env.debug,
                    responsible: signItem.data.responsible,
                    roles: this.signRolesById,
                    alignment: signItem.data.alignment,
                    required: signItem.data.required,
                    placeholder: signItem.data.placeholder,
                    id: signItem.data.id,
                    type: signItem.data.type,
                    option_ids: signItem.data.option_ids,
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
     * Updates the sign item, re-renders it and saves the template in case there were changes
     * @param {SignItem} signItem
     * @param {Object} data
     */
    updateSignItem(signItem, data) {
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
     * Deletes a sign item from the template
     * @param {SignItem} signItem
     */
    deleteSignItem(signItem) {
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
        const printButton = this.root.querySelector("#print");
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
            }
            this.signItems[page][id].data.updated = false;
        });
        this.deletedSignItemIds = [];
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
            { context: this.user.context }
        );
        for (const option of newOptions) {
            this.selectionOptionsById[option.id] = option;
        }
    }

    /**
     * Updates the local roles to include new records
     * @param {Number} id role id
     */
    async updateRoles(id) {
        if (!(id in this.signRolesById)) {
            const newRole = await this.orm.searchRead("sign.item.role", [["id", "=", id]], [], {
                context: this.user.context,
            });
            this.signRolesById[newRole[0].id] = newRole[0];
        }
    }
}
