import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { AnchorDialog } from "./anchor_dialog";
import { getElementsWithOption } from "@html_builder/utils/utils";

const anchorSelector = ":not(p).oe_structure > *, :not(p)[data-oe-type=html] > *";
const anchorExclude =
    ".modal *, .oe_structure .oe_structure *, [data-oe-type=html] .oe_structure *, .s_popup";

export function canHaveAnchor(element) {
    return element.matches(anchorSelector) && !element.matches(anchorExclude);
}

export class AnchorPlugin extends Plugin {
    static id = "anchor";
    static dependencies = ["history"];
    static shared = ["createOrEditAnchorLink"];
    resources = {
        on_cloned_handlers: this.onCloned.bind(this),
        get_options_container_top_buttons: withSequence(
            0,
            this.getOptionsContainerTopButtons.bind(this)
        ),
    };

    onCloned({ cloneEl }) {
        const anchorEls = getElementsWithOption(cloneEl, anchorSelector, anchorExclude);
        anchorEls.forEach((anchorEl) => this.deleteAnchor(anchorEl));
    }

    getOptionsContainerTopButtons(el) {
        if (!canHaveAnchor(el)) {
            return [];
        }

        return [
            {
                class: "fa fa-fw fa-link oe_snippet_anchor btn o-hb-btn btn-accent-color-hover",
                title: _t("Create and copy a link targeting this block or edit it"),
                handler: this.createOrEditAnchorLink.bind(this),
            },
        ];
    }

    // TODO check if no other way when doing popup options.
    isModal(element) {
        return element.classList.contains("modal");
    }

    setAnchorName(element, value) {
        if (value) {
            element.id = value;
            if (!this.isModal(element)) {
                element.dataset.anchor = true;
            }
        } else {
            this.deleteAnchor(element);
        }
        this.dependencies.history.addStep();
    }

    createAnchor(element) {
        const titleEls = element.querySelectorAll("h1, h2, h3, h4, h5, h6");
        const title = titleEls.length > 0 ? titleEls[0].innerText : element.dataset.name;
        const anchorName = this.formatAnchor(title);

        let n = "";
        while (this.document.getElementById(anchorName + n)) {
            n = (n || 1) + 1;
        }

        this.setAnchorName(element, anchorName + n);
    }

    deleteAnchor(element) {
        element.removeAttribute("data-anchor");
        element.removeAttribute("id");
    }

    getAnchorLink(element) {
        const pathName = this.isModal(element) ? "" : this.document.location.pathname;
        return `${pathName}#${element.id}`;
    }

    async createOrEditAnchorLink(element) {
        if (!element.id) {
            this.createAnchor(element);
        }
        const anchorLink = this.getAnchorLink(element);
        await browser.navigator.clipboard.writeText(anchorLink);
        const message = _t("Anchor copied to clipboard%(br)sLink: %(anchorLink)s", {
            anchorLink,
            br: markup`<br>`,
        });
        const closeNotification = this.services.notification.add(message, {
            type: "success",
            buttons: [
                {
                    name: _t("Edit"),
                    primary: true,
                    onClick: () => {
                        closeNotification();
                        // Open the "rename anchor" dialog.
                        this.services.dialog.add(AnchorDialog, {
                            currentAnchorName: decodeURIComponent(element.id),
                            renameAnchor: async (anchorName) => {
                                const alreadyExists = !!this.document.getElementById(anchorName);
                                if (alreadyExists) {
                                    return false;
                                }

                                this.setAnchorName(element, anchorName);
                                await this.createOrEditAnchorLink(element);
                                return true;
                            },
                            deleteAnchor: () => {
                                this.deleteAnchor(element);
                                this.dependencies.history.addStep();
                            },
                            formatAnchor: this.formatAnchor,
                        });
                    },
                },
            ],
        });
    }

    formatAnchor(text) {
        return encodeURIComponent(text.trim().replace(/\s+/g, "-"));
    }
}
