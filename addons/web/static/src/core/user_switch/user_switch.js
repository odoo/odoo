import { Component, useRef, useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { getLastConnectedUsers, setLastConnectedUsers } from "@web/core/user";
import { imageUrl } from "@web/core/utils/urls";

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
        this.form.classList.toggle("d-none", users.length > 1);
        this.form.querySelector(":placeholder-shown")?.focus();
        useEffect(
            (el) => el?.querySelector("button.list-group-item-action")?.focus(),
            () => [this.root.el]
        );
    }

    toggleFormDisplay() {
        this.state.displayUserChoice = !this.state.displayUserChoice && this.state.users.length;
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
        this.form.querySelector("input#login").value = login;
        this.form.querySelector("input#password").value = "";
        this.toggleFormDisplay();
    }
}

registry.category("public_components").add("web.user_switch", UserSwitch);
