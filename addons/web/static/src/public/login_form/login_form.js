import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { getLastConnectedUsers, setLastConnectedUsers } from "@web/core/user";
import { imageUrl } from "@web/core/utils/urls";

export class LoginForm extends Interaction {
    static selector = ".oe_login_form_container";
    dynamicContent = {
        "form.oe_login_form": {
            "t-att-class": () => ({ "d-none": this.displayUserChoice }),
        },
        ".o_user_switch": {
            "t-att-class": () => ({ "d-none": !this.displayUserChoice }),
        },
        ".o_fill_form_btn": {
            "t-on-click": () => this.fillForm(),
        },
        ".o_user_switch_btn": {
            "t-on-click": this.toggleFormDisplay,
        },
        ".o_user_item": {
            "t-on-click": this.onClickUser,
        },
        ".o_login_btn": {
            "t-on-click": this.onClickLogin,
        },
    };

    setup() {
        this.users = getLastConnectedUsers();
        this.displayUserChoice = this.users.length > 1;
        this.form = this.el.querySelector("form.oe_login_form");
    }

    start() {
        const listEl = this.el.querySelector(".list-group");
        this.users.forEach((user) => {
            this.renderAt(
                "web.login_form.user_list_entry",
                { avatarUrl: this.getAvatarUrl(user), user },
                listEl
            );
        });
        this.waitForAnimationFrame(() => {
            this.displayUserChoice
                ? this.el.querySelector("button.list-group-item-action")?.focus()
                : this.form.querySelector(":placeholder-shown")?.focus();
        });
    }

    onClickUser(event) {
        const userId = event.currentTarget.dataset.userid;
        const isRemoving = event.target.matches(".o_remove_user_btn");
        if (isRemoving) {
            this.users = this.users.filter((user) => user.userId !== userId);
            event.currentTarget.remove();
            setLastConnectedUsers(this.users);
            if (!this.users.length) {
                this.fillForm();
            } else {
                this.waitForAnimationFrame(() => {
                    this.el.querySelector("button.list-group-item-action")?.focus();
                });
            }
        } else {
            const user = this.users.find((u) => u.userId === parseInt(userId, 10));
            this.fillForm(user.login);
        }
    }

    onClickLogin() {
        this.form.submit();
    }

    toggleFormDisplay() {
        this.displayUserChoice = !this.displayUserChoice && this.users.length;
        this.waitForAnimationFrame(() => {
            this.displayUserChoice
                ? this.el.querySelector("button.list-group-item-action")?.focus()
                : this.form.querySelector(":placeholder-shown")?.focus();
        });
    }

    getAvatarUrl({ partnerId, partnerWriteDate: unique }) {
        return imageUrl("res.partner", partnerId, "avatar_128", { unique });
    }

    fillForm(login = "") {
        this.form.querySelector("input#login").value = login;
        this.form.querySelector("input#password").value = "";
        this.toggleFormDisplay();
    }
}

registry.category("public.interactions").add("web.login_form", LoginForm);
