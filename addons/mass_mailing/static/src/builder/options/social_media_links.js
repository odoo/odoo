import { BaseOptionComponent } from "@html_builder/core/utils";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useRef, useEffect, useState } from "@odoo/owl";
import { useSortable } from "@web/core/utils/sortable_owl";
import { user } from "@web/core/user";
import { renderToElement } from "@web/core/utils/render";

export class SocialMediaLinks extends BaseOptionComponent {
    static template = "mass_mailing.SocialMediaLinks";
    static props = {
        fetchRecordedSocialMedia: { type: Function },
    };
    static components = {
        Dropdown,
    };

    /** @override */
    setup() {
        super.setup();
        this.companies = user.allowedCompanies;
        this.rootRef = useRef("root");

        const container = this.env.getEditingElement();
        const links = [];
        for (const link of container.querySelectorAll(":scope > a[href]")) {
            links.push({
                checked: true,
                element: link,
            });
        }

        const companyId = parseInt(container.getAttribute("data-company-id"));
        this.state = useState({
            links,
            selectedCompany: this.companies.find(company => {
                return company.id === companyId;
            }),
        });

        useEffect(() => {
            const container = this.env.getEditingElement();
            container.setAttribute("data-company-id", this.state.selectedCompany.id);
        }, () => [this.state.selectedCompany.id]);

        useSortable({
            ref: this.rootRef,
            elements: "tr",
            handle: ".o_drag_handle",
            cursor: "grabbing",
            placeholderClasses: ["d-table-row"],
            onDrop: ({ next, element }) => {
                const fromIndex = parseInt(element.dataset.id);
                const link = this.state.links[fromIndex];
                this.state.links.splice(fromIndex, 1);
                if (next) {
                    let toIndex = parseInt(next.dataset.id);
                    if (fromIndex < toIndex) {
                        toIndex--;
                    }
                    this.state.links.splice(toIndex, 0, link);
                } else {
                    this.state.links.push(link);
                }
                this.updateLinks();
            },
        });
    }

    updateLinks() {
        const container = this.env.getEditingElement();
        for (const link of container.querySelectorAll(":scope > a[href]")) {
            link.remove();
        }
        for (const link of this.state.links) {
            if (link.checked) {
                container.append(link.element);
            }
        }
        this.env.editor.shared.history.addStep();
    }

    /** @param {Object} company */
    async selectCompany(company) {
        const medias = await this.props.fetchRecordedSocialMedia(company.id);
        for (const [plateform, href] of Object.entries(medias)) {
            const link = this.state.links.find(({ element }) => {
                return element.getAttribute('data-plateform') === plateform;
            });
            if (link) {
                const { element } = link;
                element.href = href || "";
            } else {
                this.state.links.push({
                    checked: true,
                    element: renderToElement("mass_mailing.social_media_link", {
                        href: href || "",
                        plateform,
                        icon: `fa-${plateform}`,
                    }),
                });
            }
        }
        this.state.selectedCompany = company;
    }

    /**
     * @param {Event} event
     * @param {integer} index
     */
    onSocialMediaLinkToggle(event, index) {
        this.state.links[index].checked = !!event.target.checked;
        this.updateLinks();
    }

    /**
     * @param {Event} event
     * @param {integer} index
     */
    onSocialMediaLinkChange(event, index) {
        const { element } = this.state.links[index];
        element.href = event.target.value;
    }

    /** @param {Event} event */
    onSocialMediaLinkAdd(event) {
        this.state.links.push({
            checked: true,
            element: renderToElement("mass_mailing.social_media_link", {
                href: "http://www.example.com",
                icon: "fa-pencil",
            }),
        });
        this.updateLinks();
    }

    /**
     * @param {Event} event
     * @param {integer} index
     */
    onSocialMediaLinkDelete(event, index) {
        this.state.links.splice(index, 1);
        this.updateLinks();
    }
}
