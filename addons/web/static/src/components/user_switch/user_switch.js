// @ts-check

/** @module @web/components/user_switch/user_switch - Login page component for quick-switching between recently connected user accounts */

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import { getLastConnectedUsers, setLastConnectedUsers } from "@web/services/user";

export class UserSwitch extends Component {
    static template = "web.login_user_switch";
    static props = {};

    setup() {
        const users = getLastConnectedUsers();
        this.root = useRef("root");
        this.state = useState({
            users,
            displayUserChoice: users.length > 1,
        });
        this.form = document.querySelector("form.oe_login_form");
        // Hide form only when we have multiple users to show in user-switch panel.
        // Form is visible by default (progressive enhancement: works without JS).
        const hideForm = users.length > 1;
        this.form.classList.toggle("d-none", hideForm);
        if (!hideForm) {
            this.form.querySelector(":placeholder-shown")?.focus();
        }
        useEffect(
            (el) => el?.querySelector("button.list-group-item-action")?.focus(),
            () => [this.root.el],
        );
    }

    toggleFormDisplay() {
        this.state.displayUserChoice =
            !this.state.displayUserChoice && this.state.users.length > 0;
        this.form.classList.toggle("d-none", this.state.displayUserChoice);
        this.form.querySelector(":placeholder-shown")?.focus();
    }

    getAvatarUrl({ partnerId, partnerWriteDate: unique }) {
        return imageUrl("res.partner", partnerId, "avatar_128", { unique });
    }

    remove(deletedUser) {
        this.state.users = this.state.users.filter((user) => user !== deletedUser);
        setLastConnectedUsers(this.state.users);
        if (!this.state.users.length) {
            this.fillForm();
        }
    }

    fillForm(login = "") {
        /** @type {HTMLInputElement} */ (this.form.querySelector("input#login")).value =
            login;
        /** @type {HTMLInputElement} */ (
            this.form.querySelector("input#password")
        ).value = "";
        this.toggleFormDisplay();
    }
}

registry
    .category("public_components")
    .add("web.user_switch", /** @type {any} */ (UserSwitch));
