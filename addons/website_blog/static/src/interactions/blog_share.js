import { Interaction } from "@web/public/interaction";

import { _t } from "@web/core/l10n/translation";

export class BlogShare extends Interaction {
    dynamicContent = {
        _root: { "t-on-mouseup": this.showPopover },
        _window: { "t-on-mousedown": this.hidePopover },
    };

    setup() {
        this.options = {
            minLength: 5,
            maxLength: 140,
        };
        this.bsPopover = null;
        this.shareCommentEl = null;
        this.shareTweetEl = null;
        this.removeCommentListener = null;
        this.removeTweetListener = null;
        this.popoverContentEl = null;
    }

    showPopover() {
        if (this.getSelectionRange("string").length < this.options.minLength) {
            return;
        }
        const popoverEl = document.createElement("span");
        popoverEl.classList.add("share");
        this.popoverContentEl ||= this.makeContent();
        this.updatePopoverSelection();

        const range = this.getSelectionRange();
        range.insertNode(popoverEl);

        this.bsPopover = Popover.getOrCreateInstance(popoverEl, {
            trigger: "manual",
            placement: "top",
            html: true,
            content: () => this.popoverContentEl,
        });

        this.bsPopover.show();
        this.registerCleanup(() => {
            this.bsPopover.hide();
            this.bsPopover.dispose();
            popoverEl.remove();
        });
    }

    hidePopover() {
        if (this.bsPopover) {
            this.bsPopover.hide();
        }
    }

    /**
     * @param {"string" | null} type - whether to return a string or a Range
     * @returns {"string" | Range}
     */
    getSelectionRange(type) {
        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0) {
            return "";
        }
        if (type === "string") {
            return String(selection.getRangeAt(0)).replace(/\s{2,}/g, " ");
        } else {
            return selection.getRangeAt(0);
        }
    }

    makeContent() {
        const popoverContentEl = document.createElement("div");
        popoverContentEl.className = "h4 m-0";
        return popoverContentEl;
    }

    updatePopoverSelection() { }

    /**
     * @param {string} btnClasses
     * @param {string} iconClasses
     * @param {string} iconTitle
     */
    makeButton(btnClasses, iconClasses, iconTitle) {
        const btnEl = document.createElement("button");
        btnEl.className = btnClasses;
        const iconEl = document.createElement("span");
        iconEl.className = iconClasses;
        iconEl.title = iconEl.ariaLabel = _t(iconTitle);
        iconEl.role = "img";
        btnEl.appendChild(iconEl);
        return btnEl;
    }
}
