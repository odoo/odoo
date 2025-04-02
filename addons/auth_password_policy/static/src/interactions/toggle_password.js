import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class TogglePassword extends Interaction {
    static selector = "input.toggle-password"; // Runs only for inputs with this class

    setup() {
        debugger;
        this.initToggleButton();

    }

    /**
     * Adds the toggle button to the password input field.
     */
    initToggleButton() {
        if (this.el.dataset.toggled) return; // Prevent duplicate buttons

        this.el.setAttribute("data-toggled", "true");

        // Create the toggle button
        const toggleBtn = document.createElement("span");
        toggleBtn.innerHTML = '<i class="fa fa-eye"></i>';
        toggleBtn.classList.add("password-toggle-btn");

        // Wrap input for proper positioning
        const wrapper = document.createElement("div");
        wrapper.classList.add("password-wrapper");

        // Insert elements in the DOM
        this.el.parentNode.insertBefore(wrapper, this.el);
        wrapper.appendChild(this.el);
        wrapper.appendChild(toggleBtn);

        // Attach event listener
        toggleBtn.addEventListener("click", (ev) => this.onTogglePassword(ev, this.el));
    }

    /**
     * Toggles password visibility.
     */
    onTogglePassword(ev, inputField) {
        const eyeIcon = ev.currentTarget.querySelector("i");

        // Toggle password field type
        inputField.type = inputField.type === "password" ? "text" : "password";

        // Toggle eye icon classes
        eyeIcon.classList.toggle("fa-eye");
        eyeIcon.classList.toggle("fa-eye-slash");
    }
}

// ✅ Register the interaction in Odoo
registry.category("public.interactions").add("auth_password_policy.toggle_password", TogglePassword);
