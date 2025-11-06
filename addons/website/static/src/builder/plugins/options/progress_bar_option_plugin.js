import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { clamp } from "@web/core/utils/numbers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class ProgressBarOption extends BaseOptionComponent {
    static template = "website.ProgressBarOption";
    static selector = ".s_progress_bar";

    static cleanForSave(editingEl) {
        const progressBar = editingEl.querySelector(".progress-bar");
        const progressLabel = editingEl.querySelector(".s_progress_bar_text");

        if (!progressBar.classList.contains("progress-bar-striped")) {
            progressBar.classList.remove("progress-bar-animated");
        }

        if (progressLabel && progressLabel.classList.contains("d-none")) {
            progressLabel.remove();
        }
    }
}

class ProgressBarOptionPlugin extends Plugin {
    static id = "progressBarOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: ProgressBarOption,
        builder_actions: {
            DisplayAction,
            ProgressBarValueAction,
        },
        so_content_addition_selector: [".s_progress_bar"],
    };
}

export class DisplayAction extends BuilderAction {
    static id = "display";
    apply({ editingElement, params: { mainParam: position } }) {
        // retro-compatibility
        if (editingElement.classList.contains("progress")) {
            editingElement.classList.remove("progress");
            const progressBarEl = editingElement.querySelector(".progress-bar");
            if (progressBarEl) {
                const wrapperEl = document.createElement("div");
                wrapperEl.classList.add("progress");
                progressBarEl.parentNode.insertBefore(wrapperEl, progressBarEl);
                wrapperEl.appendChild(progressBarEl);
                editingElement
                    .querySelector(".progress-bar span")
                    .classList.add("s_progress_bar_text");
            }
        }

        const progress = editingElement.querySelector(".progress");
        const progressValue = progress.getAttribute("aria-valuenow");
        let progressLabel = editingElement.querySelector(".s_progress_bar_text");

        if (!progressLabel && position !== "none") {
            progressLabel = document.createElement("span");
            progressLabel.classList.add("s_progress_bar_text", "small");
            progressLabel.textContent = progressValue + "%";
        }

        if (position === "inline") {
            editingElement.querySelector(".progress-bar").appendChild(progressLabel);
        } else if (["below", "after"].includes(position)) {
            progress.insertAdjacentElement("afterend", progressLabel);
        }

        // Added to address the prior omission of s_progress_bar_text in s_numbers_charts
        if (progressLabel) {
            // Temporary hide the label. It's effectively removed in cleanForSave
            // if the option is confirmed
            progressLabel.classList.toggle("d-none", position === "none");
        }
    }
}

export class ProgressBarValueAction extends BuilderAction {
    static id = "progressBarValue";
    apply({ editingElement, value }) {
        value = parseInt(value);
        value = clamp(value, 0, 100);
        const progressBarEl = editingElement.querySelector(".progress-bar");
        const progressBarTextEl = editingElement.querySelector(".s_progress_bar_text");
        const progressMainEl = editingElement.querySelector(".progress");
        // Added to address the prior omission of s_progress_bar_text in s_numbers_charts
        if (progressBarTextEl) {
            // Target precisely the XX% not only XX to not replace wrong element
            // eg 'Since 1978 we have completed 45%' <- don't replace 1978
            progressBarTextEl.innerText = progressBarTextEl.innerText.replace(
                /[0-9]+%/,
                value + "%"
            );
        }
        progressMainEl.setAttribute("aria-valuenow", value);
        progressBarEl.style.width = value + "%";
    }
    getValue({ editingElement }) {
        return editingElement.querySelector(".progress").getAttribute("aria-valuenow");
    }
}

registry.category("website-plugins").add(ProgressBarOptionPlugin.id, ProgressBarOptionPlugin);
