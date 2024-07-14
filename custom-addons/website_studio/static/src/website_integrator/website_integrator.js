/** @odoo-module */
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";

class WebsiteIntegrator extends Component {
    static template = "website_studio.WebsiteIntegrator";
    static props = { ...standardActionServiceProps };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.studio = useService("studio");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");
        this.notification = useService("notification");
        this.state = useState({ forms: [] });
        this.isDesigner = false;
        this.hasMultiWebsite = false;

        this.pageGroups = [
            {
                name: _t("Listings"),
                type: "listing",
                description: _t("Display records on your website, in a list or card format"),
                iconData: {
                    src: "/web_studio/static/src/img/view_type/list.png",
                    alt: "view Listing",
                },
            },
            {
                name: _t("Pages"),
                type: "single",
                description: _t(
                    "Display a detailed page for a single record on a page of your website"
                ),
                iconData: {
                    src: "/web_studio/static/src/img/view_type/form.png",
                    alt: "view Page",
                },
            },
        ];

        onWillStart(() => {
            return Promise.all([
                this.loadExistingForms(),
                this.loadWebsitePages(),
                this.user
                    .hasGroup("website.group_website_designer")
                    .then((r) => (this.isDesigner = r)),
                    this.user
                    .hasGroup("website.group_multi_website")
                    .then((r) => (this.hasMultiWebsite = r)),
            ]);
        });
    }

    get resModel() {
        return this.studio.editedAction.res_model;
    }

    async loadWebsitePages() {
        const res = await this.rpc("/website_studio/get_website_pages", {
            res_model: this.resModel,
        });

        this.state.websites = res.websites;
        this.state.pages = res.pages;
    }

    getWebsites() {
        return [{ id: false, display_name: _t("All Websites") }, ...this.state.websites];
    }

    getPages(type, websiteId) {
        return this.state.pages.filter(
            (p) =>
                p.page_type === type && ((p.website_id && p.website_id[0]) || false) === websiteId
        );
    }

    async loadExistingForms() {
        const forms = await this.rpc("/website_studio/get_forms", {
            res_model: this.resModel,
        });
        this.state.forms = forms;
    }

    async onNewForm() {
        if (this.isDesigner) {
            const url = await this.rpc("/website_studio/create_form", {
                res_model: this.resModel,
            });
            this.loadExistingForms(); // don't wait
            return this.openFormUrl(url);
        } else {
            this.notification.add(
                _t(
                    "Sorry, only users with the following" +
                        " access level are currently allowed to do that:" +
                        " 'Website/Editor and Designer'"
                ),
                {
                    title: _t("Error"),
                    type: "danger",
                }
            );
        }
    }

    openFormUrl(url) {
        return this.action.doAction({ type: "ir.actions.act_url", url: `${url}?enable_editor=1` });
    }

    computePageUrl(page) {
        let url = `/model/${page.name_slugified}`;
        if (page.page_type === "single") {
            url += "/<string:record_slug>";
        }
        return url;
    }

    openPageUrl(page) {
        return this.action.doAction({
            type: "ir.actions.act_url",
            url: `${this.computePageUrl(page)}?enable_editor=1`,
        });
    }

    onConfigurePage(page) {
        return this.action.doAction(
            {
                type: "ir.actions.act_window",
                target: "new",
                res_id: page.id,
                res_model: "website.controller.page",
                views: [[false, "form"]],
            },
            {
                onClose: () => this.loadWebsitePages(),
            }
        );
    }

    onNewPage(type, websiteId) {
        const context = {
            form_view_ref: "website_studio.website_controller_page_form_dialog_new",
            default_model: this.resModel,
            default_website_id: websiteId,
            default_page_type: type,
            default_website_published: true,
            "website_studio.create_page": true,
        };
        if (type === "listing") {
            context.default_use_menu = true;
            context.default_auto_single_page = !this.state.pages.filter(
                (p) => p.page_type === "single" && (!p.website_id || p.website_id[0] === websiteId)
            ).length;
        }

        return this.action.doAction(
            {
                type: "ir.actions.act_window",
                target: "new",
                context,
                res_model: "website.controller.page",
                views: [[false, "form"]],
            },
            {
                onClose: () => this.loadWebsitePages(),
            }
        );
    }

    async deletePage(page) {
        await this.orm.unlink("website.controller.page", [page.id]);
        this.loadWebsitePages();
    }
}

registry.category("actions").add("website_studio.action_website_integration", WebsiteIntegrator);
registry.category("web_studio.editor_tabs").add("website", {
    name: _t("Website"),
    action: "website_studio.action_website_integration",
});
