/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';
import { useService, useBus } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

const websiteSystrayRegistry = registry.category('website_systray');
const { useEffect, useState } = owl;

websiteSystrayRegistry.add("UserMenu", { Component: UserMenu }, { sequence: 14 });

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.websiteService = useService('website');
        this.websiteCustomMenus = useService('website_custom_menus');
        this.websiteContext = useState(this.websiteService.context);
        this.mutex = new Mutex();

        // The navbar is rerendered with an event, as it can not naturally be
        // with props/state (the WebsitePreview client action and the navbar
        // are not related).
        useBus(websiteSystrayRegistry, 'EDIT-WEBSITE', () => this.render(true));

        if (this.env.debug && !websiteSystrayRegistry.contains('web.debug_mode_menu')) {
            websiteSystrayRegistry.add('web.debug_mode_menu', registry.category('systray').get('web.debug_mode_menu'), {sequence: 100});
        }
        // Similar to what is done in web/navbar. When the app menu or systray
        // is updated, we need to adapt the navbar so that the "more" menu
        // can be computed.
        let adaptCounter = 0;
        const renderAndAdapt = () => {
            this.render(true);
            adaptCounter++;
        };
        useEffect(
            (adaptCounter) => {
                // We do not want to adapt on the first render
                // as the super class already does it.
                if (adaptCounter > 0) {
                    this.adapt();
                }
            },
            () => [adaptCounter]
        );

        useEffect((snippetsLoaded) => {
            const navbarMenus = this.root.el.querySelectorAll(".o_menu_sections .dropdown-toggle");
            if (snippetsLoaded) {
                // Remove numerical hotkeys on the navbar because they are used
                // in the OdooEditor.
                [...navbarMenus].forEach((el) => delete el.dataset.hotkey);

                this.clickOnNavbarController = new AbortController();
                this.root.el.addEventListener("click", this.interceptClick.bind(this),
                    { capture: true, signal: this.clickOnNavbarController.signal }
                );
                return () => this.clickOnNavbarController.abort();
            } else {
                // Reset numerical hotkeys on the navbar.
                for (let i = 0; i < navbarMenus.length; i++) {
                    const el = navbarMenus[i];
                    if (!el.dataset.hotkey) {
                        el.dataset.hotkey = i + 1;
                    }
                }
            }
        }, () => [this.websiteContext.snippetsLoaded]);

        useBus(websiteSystrayRegistry, 'CONTENT-UPDATED', renderAndAdapt);
    },

    /**
     * @override
     */
    get systrayItems() {
        if (this.websiteService.currentWebsite && this.websiteService.isRestrictedEditor) {
            return websiteSystrayRegistry
                .getEntries()
                .map(([key, value], index) => ({ key, ...value, index }))
                .filter((item) => ('isDisplayed' in item ? item.isDisplayed(this.env) : true))
                .reverse();
        }
        return super.systrayItems;
    },

    /**
     * @override
     */
    get currentAppSections() {
        const currentAppSections = super.currentAppSections;
        if (this.currentApp && this.currentApp.xmlid === 'website.menu_website_configuration') {
            return this.websiteCustomMenus.addCustomMenus(currentAppSections).filter(section => section.childrenTree.length);
        }
        return currentAppSections;
    },

    /**
     * @override
     */
    onNavBarDropdownItemSelection(menu) {
        const websiteMenu = this.websiteCustomMenus.get(menu.xmlid);
        if (websiteMenu) {
            return this.websiteCustomMenus.open(menu);
        }
        return super.onNavBarDropdownItemSelection(menu);
    },

    /**
     * Handle the action when leaving the page through the navbar while in edit
     * mode by making sure the edit panel is properly closed before leaving.
     *
     * @param {Event} ev
     */
    interceptClick(ev) {
        // Menus either useful in edit mode or harmless (no immediate page
        // switch).
        const allowedClicksInEditModeSelector = [
            ".o_top_actions_editor",
            ".o_website_publish",
            ".o_mobile_preview",
            ".o_menu_sections",
            ".o-dropdown",
        ].join(",");
        const isTargetAllowed = ev.target.closest(".o-dropdown--menu") ? false :
            ev.target.classList.contains("o_main_navbar") ||
            ev.target.closest(allowedClicksInEditModeSelector);
        if (!isTargetAllowed) {
            const onConfirmLeave = () => {
                this.clickOnNavbarController.abort();
                // SVGs do not take the click into account.
                this.mutex.exec(() => ev.target.closest(":not(svg)").click());
            };
            ev.stopPropagation();
            ev.preventDefault();
            this.websiteService.bus.trigger("LEAVE-EDIT-MODE", {
                onLeave: onConfirmLeave,
                pageLeave: true,
            });
        }
    },
});
