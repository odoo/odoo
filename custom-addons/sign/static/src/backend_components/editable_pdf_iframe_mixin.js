/** @odoo-module **/

import { renderToString } from "@web/core/utils/render";
import {
    startHelperLines,
    offset,
    normalizePosition,
    generateRandomId,
    startSmoothScroll,
    startResize,
} from "@sign/components/sign_request/utils";
import { InitialsAllPagesDialog } from "@sign/dialogs/initials_all_pages_dialog";
import { isMobileOS } from "@web/core/browser/feature_detection";

/**
 * Mixin that adds edit features into PDF_iframe classes like drag/drop, resize, helper lines
 * Currently, it should be used only for EditWhileSigningSignablePDFIframe and SignTemplateIframe
 * Parent class should implement allowEdit and saveChanges
 *
 * @param { class } pdfClass
 * @returns class
 */
export const EditablePDFIframeMixin = (pdfClass) =>
    class extends pdfClass {
        /**
         * Callback executed when a sign item is resized
         * @param {SignItem} signItem
         * @param {Object} change object with new width and height of sign item
         * @param {Boolean} end boolean indicating if the resize is done or still in progress
         */
        onResizeItem(signItem, change, end = false) {
            this.helperLines.show(signItem.el);
            Object.assign(signItem.el.style, {
                height: `${change.height * 100}%`,
                width: `${change.width * 100}%`,
            });
            Object.assign(signItem.data, {
                width: change.width,
                height: change.height,
                updated: true,
            });
            this.updateSignItemFontSize(signItem);
            if (end) {
                this.helperLines.hide();
                this.saveChanges();
            }
        }

        get allowEdit() {
            return false;
        }

        /**
         * @override
         */
        renderSignItem() {
            const signItem = super.renderSignItem(...arguments);
            if (isMobileOS()) {
                for (const node of signItem.querySelectorAll(
                    ".o_sign_config_handle, .o_resize_handler"
                )) {
                    node.classList.add("d-none");
                }
            }
            return signItem;
        }

        renderSignItems() {
            super.renderSignItems();
            if (this.allowEdit) {
                this.startDragAndDrop();
                this.helperLines = startHelperLines(this.root);
            }
        }

        startDragAndDrop() {
            this.root.querySelectorAll(".page").forEach((page) => {
                page.addEventListener("dragover", (e) => this.onDragOver(e));
                page.addEventListener("drop", (e) => this.onDrop(e));
            });

            this.root.querySelectorAll(".o_sign_field_type_button").forEach((sidebarItem) => {
                sidebarItem.setAttribute("draggable", true);
                sidebarItem.addEventListener("dragstart", (e) => this.onSidebarDragStart(e));
                sidebarItem.addEventListener("dragend", (e) => this.onSidebarDragEnd(e));
            });
        }

        onDragStart(e) {
            const signItem = e.currentTarget.parentElement.parentElement;
            const page = signItem.parentElement;
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("page", page.dataset.pageNumber);
            e.dataTransfer.setData("id", signItem.dataset.id);
            e.dataTransfer.setDragImage(signItem, 0, 0);
            // workaround to hide element while keeping the drag image visible
            requestAnimationFrame(() => {
                if (signItem) {
                    signItem.style.visibility = "hidden";
                }
            }, 0);
            this.scrollCleanup = startSmoothScroll(
                this.root.querySelector("#viewerContainer"),
                signItem,
                null,
                this.helperLines
            );
        }

        onDragEnd(e) {
            this.scrollCleanup();
        }

        onSidebarDragStart(e) {
            const signTypeElement = e.currentTarget;
            const firstPage = this.root.querySelector('.page[data-page-number="1"]');
            firstPage.insertAdjacentHTML(
                "beforeend",
                renderToString(
                    "sign.signItem",
                    this.createSignItemDataFromType(signTypeElement.dataset.itemTypeId)
                )
            );
            this.ghostSignItem = firstPage.lastChild;
            e.dataTransfer.setData("typeId", signTypeElement.dataset.itemTypeId);
            e.dataTransfer.setDragImage(this.ghostSignItem, 0, 0);
            this.scrollCleanup = startSmoothScroll(
                this.root.querySelector("#viewerContainer"),
                e.currentTarget,
                this.ghostSignItem,
                this.helperLines
            );
            // workaround to set original element to hidden while keeping the cloned element visible
            requestAnimationFrame(() => {
                if (this.ghostSignItem) {
                    this.ghostSignItem.style.visibility = "hidden";
                }
            }, 0);
        }

        onSidebarDragEnd() {
            this.scrollCleanup();
            const firstPage = this.root.querySelector('.page[data-page-number="1"]');
            firstPage.removeChild(this.ghostSignItem);
            this.ghostSignItem = false;
        }

        onDragOver(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
        }

        onDrop(e) {
            e.preventDefault();
            const page = e.currentTarget;
            const textLayer = page.querySelector(".textLayer");
            const targetPage = Number(page.dataset.pageNumber);

            const { top, left } = offset(textLayer);
            const typeId = e.dataTransfer.getData("typeId");
            if (typeId) {
                const id = generateRandomId();
                const data = this.createSignItemDataFromType(typeId);
                const posX =
                    Math.round(
                        normalizePosition((e.pageX - left) / textLayer.clientWidth, data.width) *
                            1000
                    ) / 1000;
                const posY =
                    Math.round(
                        normalizePosition((e.pageY - top) / textLayer.clientHeight, data.height) *
                            1000
                    ) / 1000;
                Object.assign(data, { id, posX, posY, page: targetPage });
                if (data.type === "initial") {
                    this.helperLines.hide();
                    return this.openDialogAfterInitialDrop(data);
                }
                this.signItems[targetPage][id] = {
                    data,
                    el: this.renderSignItem(data, page),
                };
                this.refreshSignItems();
            } else if (e.dataTransfer.getData("page") && e.dataTransfer.getData("id")) {
                const initialPage = Number(e.dataTransfer.getData("page"));
                const id = Number(e.dataTransfer.getData("id"));
                const signItem = this.signItems[initialPage][id];
                const signItemEl = signItem.el;
                const posX =
                    Math.round(
                        normalizePosition(
                            (e.pageX - left) / textLayer.clientWidth,
                            signItem.data.width
                        ) * 1000
                    ) / 1000;
                const posY =
                    Math.round(
                        normalizePosition(
                            (e.pageY - top) / textLayer.clientHeight,
                            signItem.data.height
                        ) * 1000
                    ) / 1000;

                if (initialPage !== targetPage) {
                    signItem.data.page = targetPage;
                    this.signItems[targetPage][id] = signItem;
                    delete this.signItems[initialPage][id];
                    page.appendChild(signItemEl.parentElement.removeChild(signItemEl));
                }

                Object.assign(signItem.data, {
                    posX,
                    posY,
                    updated: true,
                });
                Object.assign(signItemEl.style, {
                    top: `${posY * 100}%`,
                    left: `${posX * 100}%`,
                    visibility: "visible",
                });
            } else {
                return;
            }

            this.saveChanges();
        }

        /**
         * Enables resizing and drag/drop for sign items
         * @param {SignItem} signItem
         */
        enableCustom(signItem) {
            super.enableCustom(signItem);
            if (signItem.data.isSignItemEditable) {
                startResize(signItem, this.onResizeItem.bind(this));
                this.registerDragEventsForSignItem(signItem);
            }
        }

        openDialogAfterInitialDrop(data) {
            this.dialog.add(InitialsAllPagesDialog, {
                addInitial: (role, targetAllPages) => {
                    data.responsible = role;
                    this.currentRole = role;
                    this.addInitialSignItem(data, targetAllPages);
                },
                responsible: this.currentRole,
                roles: this.signRolesById,
            });
        }

        /**
         * Inserts initial sign items in the page
         * @param {Object} data data of the sign item to be added
         * @param {Boolean} targetAllPages if the item should be added in all pages or only at the current one
         */
        addInitialSignItem(data, targetAllPages = false) {
            if (targetAllPages) {
                for (let page = 1; page <= this.pageCount; page++) {
                    const hasSignatureItemsAtPage = Object.values(this.signItems[page]).some(
                        ({ data }) => data.type === "signature"
                    );
                    if (!hasSignatureItemsAtPage) {
                        const id = generateRandomId();
                        const signItemData = { ...data, ...{ page, id } };
                        this.signItems[page][id] = {
                            data: signItemData,
                            el: this.renderSignItem(signItemData, this.getPageContainer(page)),
                        };
                    }
                }
            } else {
                this.signItems[data.page][data.id] = {
                    data,
                    el: this.renderSignItem(data, this.getPageContainer(data.page)),
                };
            }
            this.saveChanges();
        }

        saveChanges() {}

        registerDragEventsForSignItem(signItem) {
            const handle = signItem.el.querySelector(".o_sign_config_handle");
            handle.setAttribute("draggable", true);
            handle.addEventListener("dragstart", (e) => this.onDragStart(e));
            handle.addEventListener("dragend", (e) => this.onDragEnd(e));
        }

        /**
         * Deletes a sign item from the template
         * @param {SignItem} signItem
         */
        deleteSignItem(signItem) {
            const { id, page } = signItem.data;
            signItem.el.parentElement.removeChild(signItem.el);
            delete this.signItems[page][id];
            this.saveChanges();
        }
    };
