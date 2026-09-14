/** @odoo-module native */
import { markup } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { post, rpc, RPCError } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { addLoadingEffect } from "@web/core/utils/dom/ui";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("portal.composer");

export class PortalComposer extends Interaction {
    static selector = ".o_portal_chatter_composer";
    static selectorHas = ".o_portal_chatter_composer_input";
    dynamicContent = {
        ".o_portal_chatter_file_input": {
            "t-on-change": this.onFileInputChange,
        },
        ".o_portal_chatter_attachment_btn": {
            "t-on-click": this.onAttachmentButtonClick,
        },
        ".o_portal_chatter_attachment_delete": {
            "t-on-click.prevent.stop.withTarget": this.locked(
                this.onAttachmentDeleteClick,
                true,
            ),
        },
        ".o_portal_chatter_composer_btn": {
            "t-on-click.prevent.withTarget": this.locked(this.onSubmitButtonClick),
        },
    };

    static prepareOptions(options = {}) {
        options = { ...options };
        if (typeof options.default_attachment_ids === "string") {
            options.default_attachment_ids = JSON.parse(options.default_attachment_ids);
        }
        for (const name of ["res_id", "partner_id", "pid"]) {
            if (typeof options[name] === "string") {
                options[name] = parseInt(options[name], 10);
            }
        }
        return Object.assign(
            {
                allow_composer: true,
                display_composer: false,
                csrf_token: odoo.csrf_token,
                token: false,
                res_model: false,
                res_id: false,
                send_button_label: _t("Send"),
            },
            options || {},
        );
    }

    setup() {
        this.options =
            this.env.portalComposerOptions || PortalComposer.prepareOptions({});
        this.attachments = [];
        this.pendingAttachmentOperations = 0;
        this.isPosting = false;
        this.attachmentButtonEl = this.el.querySelector(
            ".o_portal_chatter_attachment_btn",
        );
        this.fileInputEl = this.el.querySelector(".o_portal_chatter_file_input");
        this.sendButtonEl = this.el.querySelector(".o_portal_chatter_composer_btn");
        this.attachmentsEl = this.el.querySelector(
            ".o_portal_chatter_composer_input .o_portal_chatter_attachments",
        );
        this.inputTextareaEl = this.el.querySelector(
            '.o_portal_chatter_composer_input textarea[name="message"]',
        );
    }

    start() {
        if (this.options.default_attachment_ids) {
            this.attachments = this.options.default_attachment_ids.map(
                (attachment) => ({
                    ...attachment,
                    state: "done",
                }),
            );
            this.updateAttachments();
        }
    }

    onAttachmentButtonClick() {
        if (!this.isPosting) {
            this.fileInputEl.click();
        }
    }

    async onAttachmentDeleteClick(ev, currentTargetEl) {
        if (this.isPosting) {
            return;
        }
        const attachmentId = parseInt(
            currentTargetEl.closest(".o_portal_chatter_attachment").dataset.id,
            10,
        );
        const attachment = this.attachments.find(
            (attachment) => attachment.id === attachmentId,
        );
        if (!attachment) {
            return;
        }
        const accessToken = attachment.access_token;

        this._updatePendingAttachments(1);
        try {
            await this.waitFor(
                rpc("/portal/attachment/remove", {
                    attachment_id: attachmentId,
                    access_token: accessToken,
                }),
            );
            this.attachments = this.attachments.filter(
                (attachment) => attachment.id !== attachmentId,
            );
            this.updateAttachments();
        } catch (error) {
            if (error instanceof RPCError) {
                this.services.notification.add(_t("Could not remove the attachment."), {
                    type: "warning",
                });
            } else {
                throw error;
            }
        } finally {
            this._updatePendingAttachments(-1);
        }
    }

    prepareAttachmentData(file) {
        return {
            is_pending: true,
            thread_id: this.options.res_id,
            thread_model: this.options.res_model,
            token: this.options.token,
            ufile: file,
        };
    }

    async onFileInputChange() {
        if (this.isPosting) {
            this.fileInputEl.value = "";
            log.logic("discard file selection received while posting");
            return;
        }
        this._updatePendingAttachments(1);
        try {
            const results = await this.waitFor(
                Promise.allSettled(
                    [...this.fileInputEl.files].map((file) => this._uploadOne(file)),
                ),
            );
            const failure = results.find((result) => result.status === "rejected");
            if (failure) {
                throw failure.reason;
            }
        } finally {
            this.fileInputEl.value = null;
            this._updatePendingAttachments(-1);
        }
    }

    _updatePendingAttachments(delta) {
        this.pendingAttachmentOperations += delta;
        this.sendButtonEl.disabled =
            this.isPosting || this.pendingAttachmentOperations > 0;
        log.logic("pending attachments", { count: this.pendingAttachmentOperations });
    }

    async _uploadOne(file) {
        const data = this.prepareAttachmentData(file);
        if (odoo.csrf_token) {
            data.csrf_token = odoo.csrf_token;
        }
        try {
            const res = await this.waitFor(post("/mail/attachment/upload", data));
            const attachmentId = res.data["attachment_id"];
            const attachment = res.data["store_data"]["ir.attachment"].find(
                (att) => att.id === attachmentId,
            );
            attachment.state = "pending";
            this.attachments.push(attachment);
            this.updateAttachments();
        } catch (error) {
            if (error instanceof RPCError) {
                this.services.notification.add(
                    _t("Could not save file %s", markup`<strong>${file.name}</strong>`),
                    { type: "warning", sticky: true },
                );
            } else {
                throw error;
            }
        }
    }

    prepareMessageData() {
        return {
            thread_model: this.options.res_model,
            thread_id: this.options.res_id,
            post_data: {
                body: this.inputTextareaEl.value,
                attachment_ids: this.attachments.map((a) => a.id),
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
                attachment_tokens: this.attachments.map((a) => a.ownership_token),
            },
            token: this.options.token,
            hash: this.options.hash,
            pid: this.options.pid,
        };
    }

    async onSubmitButtonClick(ev, currentTargetEl) {
        if (this.isPosting || this.pendingAttachmentOperations) {
            return false;
        }
        const error = this.onSubmitCheckContent();
        if (error) {
            this.inputTextareaEl.classList.add("border-danger");
            const errorEl = this.el.querySelector(".o_portal_chatter_composer_error");
            errorEl.innerText = error;
            errorEl.classList.remove("d-none");
            return false;
        }
        this.inputTextareaEl.classList.remove("border-danger");
        this.el
            .querySelector(".o_portal_chatter_composer_error")
            ?.classList.add("d-none");
        const restoreLoading = addLoadingEffect(this.sendButtonEl);
        const attachmentControls = [
            this.attachmentButtonEl,
            this.fileInputEl,
            ...this.el.querySelectorAll(".o_portal_chatter_attachment_delete"),
        ]
            .filter(Boolean)
            .map((element) => ({ element, disabled: element.disabled }));
        for (const { element } of attachmentControls) {
            element.disabled = true;
        }
        this.isPosting = true;
        log.logic("posting with attachment controls locked");
        try {
            return await this.chatterPostMessage(currentTargetEl.dataset.action);
        } finally {
            restoreLoading();
            this.isPosting = false;
            this.sendButtonEl.disabled = this.pendingAttachmentOperations > 0;
            for (const { element, disabled } of attachmentControls) {
                element.disabled = disabled;
            }
        }
    }

    onSubmitCheckContent() {
        if (!this.inputTextareaEl.value.trim() && !this.attachments.length) {
            return _t(
                "Some fields are required. Please make sure to write a message or attach a document",
            );
        }
    }

    updateAttachments() {
        this.attachmentsEl.replaceChildren();
        this.renderAt(
            "portal.Chatter.Attachments",
            {
                attachments: this.attachments,
                showDelete: true,
            },
            this.attachmentsEl,
        );
    }

    /**
     * @param {String} route
     * @returns {Promise}
     */
    async chatterPostMessage(route) {
        const result = await this.waitFor(rpc(route, this.prepareMessageData()));
        const res = result.store_data || result;
        this.env.bus.trigger("reload_chatter_content", res);
        return res;
    }
}

registry.category("public.interactions").add("portal.portal_composer", PortalComposer);
