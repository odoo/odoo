import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { post } from "@web/core/network/http_service";
import { Component, markup } from "@odoo/owl";
import { rpc, RPCError } from "@web/core/network/rpc";

/**
 * Display the composer (according to access right)
 */
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
            "t-on-click.prevent.stop.withTarget": this.locked(this.onAttachmentDeleteClick, true),
        },
        ".o_portal_chatter_composer_btn": {
            "t-on-click.prevent.withTarget": this.locked(this.onSubmitButtonClick, true),
        },
    };

    static prepareOptions(options) {
        if (typeof options.default_attachment_ids === "string") {
            options.default_attachment_ids = JSON.parse(options.default_attachment_ids);
        }
        for (const name of ["res_id", "partner_id", "pid"]) {
            if (typeof options[name] === "string") {
                options[name] = parseInt(options[name]);
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
            options || {}
        );
    }

    setup() {
        this.options = this.env.portalComposerOptions || PortalComposer.prepareOptions({});
        this.attachments = [];
        this.attachmentButtonEl = this.el.querySelector(".o_portal_chatter_attachment_btn");
        this.fileInputEl = this.el.querySelector(".o_portal_chatter_file_input");
        this.sendButtonEl = this.el.querySelector(".o_portal_chatter_composer_btn");
        this.attachmentsEl = this.el.querySelector(
            ".o_portal_chatter_composer_input .o_portal_chatter_attachments"
        );
        this.inputTextareaEl = this.el.querySelector(
            '.o_portal_chatter_composer_input textarea[name="message"]'
        );
    }

    start() {
        if (this.options.default_attachment_ids) {
            this.attachments = this.options.default_attachment_ids || [];
            for (const attachment of this.attachments) {
                attachment.state = "done";
            }
            this.updateAttachments();
        }
    }

    onAttachmentButtonClick() {
        this.fileInputEl.click();
    }

    async onAttachmentDeleteClick(ev, currentTargetEl) {
        const attachmentId = parseInt(
            currentTargetEl.closest(".o_portal_chatter_attachment").dataset.id
        );
        const accessToken = this.attachments.find(
            (attachment) => attachment.id === attachmentId
        ).access_token;

        this.sendButtonEl.disabled = true;

        await this.waitFor(
            rpc("/portal/attachment/remove", {
                attachment_id: attachmentId,
                access_token: accessToken,
            })
        );
        this.attachments = this.attachments.filter((attachment) => attachment.id !== attachmentId);
        this.updateAttachments();
        this.sendButtonEl.disabled = false;
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
        this.sendButtonEl.disabled = true;

        await this.waitFor(
            Promise.all(
                [...this.fileInputEl.files].map(
                    (file) =>
                        new Promise((resolve, reject) => {
                            const data = this.prepareAttachmentData(file);
                            if (odoo.csrf_token) {
                                data.csrf_token = odoo.csrf_token;
                            }
                            this.waitFor(post("/mail/attachment/upload", data))
                                .then((res) => {
                                    const attachmentId = res.data["attachment_id"];
                                    const attachment = res.data["store_data"]["ir.attachment"].find(
                                        (att) => att.id === attachmentId
                                    );
                                    attachment.state = "pending";
                                    this.attachments.push(attachment);
                                    this.updateAttachments();
                                    resolve();
                                })
                                .catch((error) => {
                                    if (error instanceof RPCError) {
                                        this.services.notification.add(
                                            _t(
                                                "Could not save file %s",
                                                markup`<strong>${file.name}</strong>`
                                            ),
                                            { type: "warning", sticky: true }
                                        );
                                        resolve();
                                    }
                                });
                        })
                )
            )
        );
        // ensures any selection triggers a change, even if the same files are selected again
        this.fileInputEl.value = null;
        this.sendButtonEl.disabled = false;
    }

    prepareMessageData() {
        return {
            thread_model: this.options.res_model,
            thread_id: this.options.res_id,
            post_data: {
                body: this.el.querySelector('textarea[name="message"]').value,
                attachment_ids: this.attachments.map((a) => a.id),
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            attachment_tokens: this.attachments.map((a) => a.ownership_token),
            token: this.options.token,
            hash: this.options.hash,
            pid: this.options.pid,
        };
    }

    async onSubmitButtonClick(ev, currentTargetEl) {
        const error = this.onSubmitCheckContent();
        if (error) {
            this.inputTextareaEl.classList.add("border-danger");
            const errorEl = this.el.querySelector(".o_portal_chatter_composer_error");
            errorEl.innerText = error;
            errorEl.classList.remove("d-none");
            return Promise.reject();
        } else {
            return this.chatterPostMessage(currentTargetEl.dataset.action);
        }
    }

    onSubmitCheckContent() {
        if (!this.inputTextareaEl.value.trim() && !this.attachments.length) {
            return _t(
                "Some fields are required. Please make sure to write a message or attach a document"
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
            this.attachmentsEl
        );
    }

    /**
     * post message using rpc call and display new message and message count
     *
     * @param {String} route
     * @returns {Promise}
     */
    async chatterPostMessage(route) {
        const result = await this.waitFor(rpc(route, this.prepareMessageData()));
        const res = result.store_data || result;
        Component.env.bus.trigger("reload_chatter_content", res);
        return res;
    }
}

registry.category("public.interactions").add("portal.portal_composer", PortalComposer);
