import { registry } from "@web/core/registry";
import { LoginForm } from "@web/public/login_form/login_form";

const LoginFormEdit = (I) =>
    class extends I {
        setup() {
            this.displayUserChoice = false;

            // Save the text content of the core elements to restore them if
            // they are emptied during edition
            this.elementsToRestore = [
                {
                    el: this.el.querySelector(".o_user_switch_btn"),
                },
                {
                    el: this.el.querySelector(".o_reset_password_btn"),
                },
                {
                    el: this.el.querySelector("label[for='login']"),
                },
                {
                    el: this.el.querySelector("label[for='password']"),
                },
            ];
            this.elementsToRestore.forEach((item) => {
                item.content = item.el?.innerText || "";
            });
        }

        // This edit interaction should do nothing at start
        start() {}

        destroy() {
            // Restore the content of the elements if they are empty
            this.elementsToRestore.forEach((item) => {
                if (item.el && (!item.el.innerText || item.el.innerText.trim() === "")) {
                    console.log("restoring", item.el);
                    item.el.innerHTML = item.content;
                }
            });
        }

        // The two following click hanlders should do nothing in edit mode
        toggleFormDisplay() {}
        onClickLogin() {}
    };

registry.category("public.interactions.edit").add("website.login_form", {
    Interaction: LoginForm,
    mixin: LoginFormEdit,
});
