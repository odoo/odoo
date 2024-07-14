/** @odoo-module */

import { KnowledgeSidebarRow } from "./sidebar_row";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, useChildSubEnv } from "@odoo/owl";

/**
 * This file defines the different sections used in the sidebar.
 * Each section is responsible of displaying an array of root articles and
 * their children.
 */

export class KnowledgeSidebarSection extends Component {
    static props = {
        rootIds: Array,
        unfoldedIds: Set,
        record: Object,
    };
    static components = {
        KnowledgeSidebarRow,
    };

    setup() {
        super.setup();
        this.userService = useService("user");
        onWillStart(async () => {
            this.isInternalUser = await this.userService.hasGroup('base.group_user');
        });
    }
}

export class KnowledgeSidebarFavoriteSection extends KnowledgeSidebarSection {
    static template = "knowledge.SidebarFavoriteSection";
    
    setup() {
        super.setup();

        // (Un)fold in the favorite tree by default.
        useChildSubEnv({
            fold: id => this.env.fold(id, true),
            unfold: id => this.env.unfold(id, true),
        });
    }
}

export class KnowledgeSidebarWorkspaceSection extends KnowledgeSidebarSection {
    static template = "knowledge.SidebarWorkspaceSection";
    
    setup() {
        super.setup();
        this.command = useService("command");
    }

    createRoot() {
        this.env.createArticle("workspace");
    }

    searchHiddenArticle() {
        this.command.openMainPalette({searchValue: "$"});
    }
}

export class KnowledgeSidebarSharedSection extends KnowledgeSidebarSection {
    static template = "knowledge.SidebarSharedSection";
}

export class KnowledgeSidebarPrivateSection extends KnowledgeSidebarSection {
    static template = "knowledge.SidebarPrivateSection";

    createRoot() {
        this.env.createArticle("private");
    }
}
