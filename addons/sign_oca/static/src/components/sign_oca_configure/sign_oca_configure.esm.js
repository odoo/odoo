/** @odoo-module QWeb **/

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {SignOcaConfigureFieldDialog} from "./sign_oca_configure_field_dialog.esm";
import {isMobileOS} from "@web/core/browser/feature_detection";
import SignOcaPdfCommon from "../sign_oca_pdf_common/sign_oca_pdf_common.esm.js";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {renderToString} from "@web/core/utils/render";
export default class SignOcaConfigure extends SignOcaPdfCommon {
    setup() {
        this.res_id =
            this.props.action.params.res_id || this.props.action.context.active_id;
        this.model =
            this.props.action.params.res_model ||
            this.props.action.context.active_model;
        super.setup(...arguments);
        this.field_template = "sign_oca.sign_iframe_field_configure";
        this.contextMenu = undefined;
        this.isMobile = isMobileOS();
    }
    postIframeFields() {
        super.postIframeFields(...arguments);
        $.each(
            this.iframe.el.contentDocument.getElementsByClassName("page"),
            (index, page) => {
                page.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                });
                page.addEventListener("contextmenu", (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (this.contextMenu !== undefined) {
                        this.contextMenu.remove();
                        this.contextMenu = undefined;
                    }
                    var position = page.getBoundingClientRect();
                    this.contextMenu = $(
                        renderToString("sign_oca.sign_iframe_contextmenu", {
                            page,
                            e,
                            left: ((e.pageX - position.x) * 100) / position.width + "%",
                            top: ((e.pageY - position.y) * 100) / position.height + "%",
                            info: this.info,
                            page_id: parseInt(page.dataset.pageNumber, 10),
                        })
                    );
                    page.append(this.contextMenu[0]);
                });
            }
        );
        this.iframe.el.contentDocument.addEventListener(
            "click",
            (ev) => {
                if (this.contextMenu && !this.creatingItem) {
                    if (
                        this.contextMenu[0].contains(ev.target) &&
                        ev.target.dataset.page
                    ) {
                        this.creatingItem = true;
                        this.orm
                            .call(this.model, "add_item", [
                                [this.res_id],
                                {
                                    field_id: parseInt(ev.target.dataset.field, 10),
                                    page: parseInt(ev.target.dataset.page, 10),
                                    position_x: parseFloat(
                                        ev.target.parentElement.style.left
                                    ),
                                    position_y: parseFloat(
                                        ev.target.parentElement.style.top
                                    ),
                                    width: 20,
                                    height: 1.5,
                                },
                            ])
                            .then((data) => {
                                this.info.items[data.id] = data;
                                this.postIframeField(data);
                                this.contextMenu.remove();
                                this.contextMenu = undefined;
                                this.creatingItem = false;
                            });
                    } else {
                        this.contextMenu.remove();
                        this.contextMenu = undefined;
                    }
                }
            },
            // We need to enforce it to happen no matter what
            true
        );
        this.iframeLoaded.resolve();
    }
    postIframeField(item) {
        var signatureItem = super.postIframeField(...arguments);
        var dragItem =
            signatureItem[0].getElementsByClassName("o_sign_oca_draggable")[0];
        var resizeItems = signatureItem[0].getElementsByClassName("o_sign_oca_resize");
        signatureItem[0].addEventListener(
            "click",
            (e) => {
                if (
                    e.target.classList.contains("o_sign_oca_resize") ||
                    e.target.classList.contains("o_sign_oca_draggable")
                ) {
                    return;
                }
                var target = e.currentTarget;
                // TODO: Open Dialog for configuration
                this.dialogService.add(SignOcaConfigureFieldDialog, {
                    title: _t("Edit field"),
                    item,
                    info: this.info,
                    confirm: async (field_id, role_id, required, placeholder) => {
                        await this.orm.call(this.model, "set_item_data", [
                            [this.res_id],
                            item.id,
                            {
                                field_id,
                                role_id,
                                required,
                                placeholder,
                            },
                        ]);
                        item.field_id = field_id;
                        item.name = this.info.fields.filter(
                            (field) => field.id === field_id
                        )[0].name;
                        item.role_id = role_id;
                        item.required = required;
                        item.placeholder = placeholder;
                        target.remove();
                        this.postIframeField(item);
                    },
                    delete: async () => {
                        await this.orm.call(this.model, "delete_item", [
                            [this.res_id],
                            item.id,
                        ]);
                        delete this.info.items[item.id];
                        target.remove();
                    },
                });
            },
            true
        );
        var startFunction = "mousedown";
        var endFunction = "mouseup";
        var moveFunction = "mousemove";
        if (this.isMobile) {
            startFunction = "touchstart";
            endFunction = "touchend";
            moveFunction = "touchmove";
        }
        dragItem.addEventListener(startFunction, (mousedownEvent) => {
            mousedownEvent.preventDefault();
            var parentPage = mousedownEvent.target.parentElement.parentElement;
            this.movingItem = mousedownEvent.target.parentElement;
            var mousemove = this._onDragItem.bind(this);
            parentPage.addEventListener(moveFunction, mousemove);
            parentPage.addEventListener(
                endFunction,
                (mouseupEvent) => {
                    mouseupEvent.currentTarget.removeEventListener(
                        moveFunction,
                        mousemove
                    );
                    var target = $(this.movingItem);
                    var position = target.parent()[0].getBoundingClientRect();
                    var newPosition = mouseupEvent;
                    if (mouseupEvent.changedTouches) {
                        newPosition = mouseupEvent.changedTouches[0];
                    }
                    var left =
                        (Math.max(
                            0,
                            Math.min(position.width, newPosition.pageX - position.x)
                        ) *
                            100) /
                        position.width;
                    var top =
                        (Math.max(
                            0,
                            Math.min(position.height, newPosition.pageY - position.y)
                        ) *
                            100) /
                        position.height;
                    target.css("left", left + "%");
                    target.css("top", top + "%");
                    item.position_x = left;
                    item.position_y = top;

                    this.orm.call(this.model, "set_item_data", [
                        [this.res_id],
                        item.id,
                        {
                            position_x: left,
                            position_y: top,
                        },
                    ]);
                    this.movingItem = undefined;
                },
                {once: true}
            );
        });
        $.each(resizeItems, (index, resizeItem) => {
            resizeItem.addEventListener(startFunction, (mousedownEvent) => {
                mousedownEvent.preventDefault();
                var parentPage = mousedownEvent.target.parentElement.parentElement;
                this.resizingItem = mousedownEvent.target.parentElement;
                var mousemove = this._onResizeItem.bind(this);
                parentPage.addEventListener(moveFunction, mousemove);
                parentPage.addEventListener(
                    endFunction,
                    (mouseupEvent) => {
                        mouseupEvent.stopPropagation();
                        mouseupEvent.preventDefault();
                        mouseupEvent.currentTarget.removeEventListener(
                            moveFunction,
                            mousemove
                        );
                        var target = $(this.resizingItem);
                        var newPosition = mouseupEvent;
                        if (mouseupEvent.changedTouches) {
                            newPosition = mouseupEvent.changedTouches[0];
                        }
                        var targetPosition = target
                            .find(".o_sign_oca_resize")[0]
                            .getBoundingClientRect();
                        var itemPosition = target[0].getBoundingClientRect();
                        var pagePosition = target.parent()[0].getBoundingClientRect();
                        var width =
                            (Math.max(
                                0,
                                newPosition.pageX +
                                    targetPosition.width -
                                    itemPosition.x
                            ) *
                                100) /
                            pagePosition.width;
                        var height =
                            (Math.max(
                                0,
                                newPosition.pageY +
                                    targetPosition.height -
                                    itemPosition.y
                            ) *
                                100) /
                            pagePosition.height;
                        target.css("width", width + "%");
                        target.css("height", height + "%");
                        item.width = width;
                        item.height = height;
                        this.orm.call(this.model, "set_item_data", [
                            [this.res_id],
                            item.id,
                            {
                                width: width,
                                height: height,
                            },
                        ]);
                    },
                    {once: true}
                );
            });
        });
        return signatureItem;
    }
    _onResizeItem(e) {
        e.stopPropagation();
        e.preventDefault();
        var target = $(this.resizingItem);
        var targetPosition = target
            .find(".o_sign_oca_resize")[0]
            .getBoundingClientRect();
        var itemPosition = target[0].getBoundingClientRect();
        var newPosition = e;
        if (e.targetTouches) {
            newPosition = e.targetTouches[0];
        }
        var pagePosition = target.parent()[0].getBoundingClientRect();
        var width =
            (Math.max(0, newPosition.pageX + targetPosition.width - itemPosition.x) *
                100) /
            pagePosition.width;
        var height =
            (Math.max(0, newPosition.pageY + targetPosition.height - itemPosition.y) *
                100) /
            pagePosition.height;
        target.css("width", width + "%");
        target.css("height", height + "%");
    }
    _onDragItem(e) {
        e.stopPropagation();
        e.preventDefault();
        var target = $(this.movingItem);
        var position = target.parent()[0].getBoundingClientRect();
        var newPosition = e;
        if (e.targetTouches) {
            newPosition = e.targetTouches[0];
        }
        var left =
            (Math.max(0, Math.min(position.width, newPosition.pageX - position.x)) *
                100) /
            position.width;
        var top =
            (Math.max(0, Math.min(position.height, newPosition.pageY - position.y)) *
                100) /
            position.height;
        target.css("left", left + "%");
        target.css("top", top + "%");
    }
}
SignOcaConfigure.template = "sign_oca.SignOcaConfigure";
SignOcaConfigure.components = {...SignOcaPdfCommon.components, ControlPanel};
SignOcaConfigure.props = [];
SignOcaConfigure.props = {
    action: Object,
    "*": {optional: true},
};
registry.category("actions").add("sign_oca_configure", SignOcaConfigure);
