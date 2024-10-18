import {
    Component,
    onWillDestroy,
    onWillStart,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { LazyComponent } from "@web/core/assets";
import { WebsiteSystrayItem } from "./website_systray_item";

function unslugHtmlDataObject(repr) {
    const match = repr && repr.match(/(.+)\((\d+),(.*)\)/);
    if (!match) {
        return null;
    }
    return {
        model: match[1],
        id: match[2] | 0,
    };
}

class WebsiteBuilder extends Component {
    static template = "mysterious_egg.WebsiteBuilder";
    static components = { LazyComponent };

    setup() {
        this.orm = useService("orm");
        this.websiteContent = useRef("iframe");
        useSubEnv({
            builderRef: useRef("container"),
        });
        this.state = useState({ isEditing: false });

        onWillStart(async () => {
            const slugCurrentWebsite = await this.orm.call(
                "website",
                "get_current_website",
            );
            this.backendWebsiteId = unslugHtmlDataObject(slugCurrentWebsite).id;
            this.initialUrl = `/website/force/${encodeURIComponent(this.backendWebsiteId)}`;
        });
        this.addSystrayItems();
        onWillDestroy(() => {
            registry.category("systray").remove("website.WebsiteSystrayItem");
        });
    }

    get menuProps() {
        return {
            iframe: this.websiteContent.el,
            closeEditor: this.closeEditor.bind(this),
        };
    }

    addSystrayItems() {
        const systrayProps = {
            onNewPage: this.onNewPage.bind(this),
            onEditPage: this.onEditPage.bind(this),
        };
        registry
            .category("systray")
            .add(
                "website.WebsiteSystrayItem",
                { Component: WebsiteSystrayItem, props: systrayProps },
                { sequence: -100 },
            );
    }

    closeEditor() {
        document.querySelector(".o_main_navbar").removeAttribute("style");
        this.state.isEditing = false;
        this.addSystrayItems();
    }

    onNewPage() {
        console.log("todo: new page");
    }

    onEditPage() {
        document.querySelector(".o_main_navbar").setAttribute("style", "margin-top: -100%;");
        setTimeout(() => {
            this.state.isEditing = true;
            registry.category("systray").remove("website.WebsiteSystrayItem");
        }, 200);
    }

    onIframeLoad(ev) {
        // history.pushState(null, "", ev.target.contentWindow.location.pathname);
    }
}

registry.category("actions").add("egg_website_preview", WebsiteBuilder);
