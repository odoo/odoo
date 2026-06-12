import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

const teamBoardContactMethodsCategory = registry.category("team_board_contact_methods");

const sendMessageContactMethod = {
    id: "sendMessage",
    label: _t("Send a message"),
    loadingLabel: _t("Sending..."),
    errorMessage: _t("Could not send your message."),
    async run({ interaction, memberId }) {
        const response = await interaction.waitFor(
            rpc("/website/team_board/contact", {
                member_id: memberId,
            })
        );
        if (!response?.success) {
            throw new Error(response?.error || "contact_failed");
        }
        return {
            closeModal: true,
            successMessage: _t("Your message has been sent."),
        };
    },
};

function getExtraTeamBoardContactMethods() {
    return teamBoardContactMethodsCategory
        .getEntries()
        .map(([id, contactMethod]) => ({ id, ...contactMethod }));
}

export class TeamBoardModal extends Interaction {
    static selector = ".s_team_board_modal";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _envBus: () => this.env.bus,
    };
    dynamicContent = {
        _envBus: {
            "t-on-WEBSITE:TEAM_BOARD:MODAL:SHOW": this.onShowModal,
        },
        _root: {
            "t-on-hidden.bs.modal": this.onModalHidden,
        },
        ".s_team_board_modal_name": {
            "t-out": () => this.member.name,
        },
        ".s_team_board_modal_role": {
            "t-out": () => this.member.role,
        },
        ".s_team_board_modal_bio": {
            "t-out": () => this.member.bio,
        },
        ".s_team_board_modal_image": {
            "t-att-src": () => this.member.imageSrc || null,
            "t-att-alt": () => this.member.imageAlt,
        },
        ".s_team_board_contact_methods": {
            "t-on-click": this.locked(this.onContactMethodClick, true),
        },
        ".s_team_board_contact_method_button": {
            "t-att-disabled": () => this.isSendingContact,
            "t-out": (buttonEl) => this.getContactMethodButtonLabel(buttonEl),
        },
    };

    setup() {
        this.isSendingContact = false;
        this.isClosing = false;
        this.member = {};
        this.activeMemberEl = null;
        this.activeContactMethodId = null;
        this.bsModal = null;
        this.extraContactMethods = getExtraTeamBoardContactMethods();
        this.contactMethods = [sendMessageContactMethod, ...this.extraContactMethods];
        this.contactMethodsById = new Map(
            this.contactMethods.map((contactMethod) => [contactMethod.id, contactMethod])
        );
        this.renderExtraContactMethods();
        this.registerCleanup(() => {
            this.isSendingContact = false;
            this.bsModal?.dispose();
            this.bsModal = null;
            this.el.remove();
        });
    }

    onShowModal(ev) {
        const state = ev.detail;
        if (!state || state.modalEl !== this.el) {
            return;
        }
        this.member = { ...state.member };
        this.activeMemberEl = state.memberEl || null;
        this.activeContactMethodId = null;
        this.updateContent();
        this.showModal();
    }

    async onContactMethodClick(ev) {
        const buttonEl = ev.target.closest(".s_team_board_contact_method_button");
        if (!buttonEl) {
            return;
        }
        const requestedMethodId = buttonEl.dataset.contactMethodId;
        const requestedMethod = this.contactMethodsById.get(requestedMethodId);
        this.isSendingContact = true;
        this.activeContactMethodId = requestedMethodId;
        this.updateContent();
        try {
            const response = await this.waitFor(
                requestedMethod.run({
                    interaction: this,
                    memberEl: this.activeMemberEl,
                    memberId: this.member.memberId,
                })
            );
            this.services.notification.add(response?.successMessage || _t("Action completed."), {
                type: "success",
            });
            if (response?.closeModal) {
                this.closeModal();
            }
        } catch {
            if (!this.isDestroyed) {
                this.services.notification.add(
                    requestedMethod.errorMessage || _t("Could not process your request."),
                    {
                        type: "danger",
                    }
                );
            }
        } finally {
            this.isSendingContact = false;
            this.activeContactMethodId = null;
        }
    }

    renderExtraContactMethods() {
        const extraContactMethodsEl = this.el.querySelector(".s_team_board_extra_contact_methods");
        extraContactMethodsEl.replaceChildren();
        this.renderAt(
            "website.s_team_board.extra_contact_methods",
            { contactMethods: this.extraContactMethods },
            extraContactMethodsEl
        );
    }

    getContactMethodButtonLabel(buttonEl) {
        const methodId = buttonEl.dataset.contactMethodId;
        const contactMethod = this.contactMethodsById.get(methodId);
        return this.isSendingContact && this.activeContactMethodId === methodId
            ? contactMethod.loadingLabel || _t("Working...")
            : contactMethod.label;
    }

    showModal() {
        this.bsModal = window.Modal.getOrCreateInstance(this.el);
        this.bsModal.show();
    }

    onModalHidden() {
        if (this.isClosing) {
            return;
        }
        this.isClosing = true;
        this.services["public.interactions"].stopInteractions(this.el);
    }

    closeModal() {
        if (this.isClosing) {
            return;
        }
        this.bsModal?.hide();
    }
}

registry.category("public.interactions").add("website.team_board_modal", TeamBoardModal);
