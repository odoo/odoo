/** @odoo-module */

import { components, helpers } from "@odoo/o-spreadsheet";
import { Component, useRef, useState, useEffect } from "@odoo/owl";
import { formatToLocaleString } from "../../helpers";
import { _t } from "@web/core/l10n/translation";
import { pyToJsLocale } from "@web/core/l10n/utils";

const { createActions } = helpers;

export class VersionHistoryItem extends Component {
    static template = "spreadsheet_edition.VersionHistoryItem";
    static components = { Menu: components.Menu };
    static props = {
        active: Boolean,
        revision: Object,
        onActivation: { optional: true, type: Function },
        onBlur: { optional: true, type: Function },
    };
    setup() {
        this.menuState = useState({
            isOpen: false,
            position: null,
        });
        this.state = useState({ editName: this.defaultName });
        this.inputRef = useRef("revisionName");
        this.menuButtonRef = useRef("menuButton");
        this.itemRef = useRef("item");

        useEffect(() => {
            if (this.props.active) {
                this.itemRef.el.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                    inline: "nearest",
                });
            }
        });
    }

    get revision() {
        return this.props.revision;
    }

    get defaultName() {
        return (
            this.props.revision.name || this.formatRevisionTimeStamp(this.props.revision.timestamp)
        );
    }

    get isLatestVersion() {
        return (
            this.env.historyManager.getRevisions()[0].nextRevisionId ===
            this.revision.nextRevisionId
        );
    }

    get dateValue() {
        return this.isLatestVersion
            ? _t("Current Version")
            : this.formatRevisionTimeStamp(this.props.revision.timestamp);
    }

    onKeyDown(ev) {
        switch (ev.key) {
            case "Enter":
                this.renameRevision();
                this.props.onBlur?.();
                break;
            case "Escape":
                this.state.editName = this.defaultName;
                this.props.onBlur?.();
                break;
        }
    }

    renameRevision() {
        if (!this.state.editName) {
            this.state.editName = this.defaultName;
        }
        if (this.state.editName !== this.defaultName) {
            this.env.historyManager.renameRevision(this.revision.id, this.state.editName);
        }
    }

    get menuItems() {
        return createActions([
            {
                name: this.revision.name ? _t("Rename") : _t("Name this version"),
                execute: () => {
                    this.inputRef.el.focus();
                },
                isReadonlyAllowed: true,
            },
            {
                name: _t("Make a copy"),
                execute: (env) => {
                    env.historyManager.forkHistory(this.revision.id);
                },
                isReadonlyAllowed: true,
            },
        ]);
    }

    openMenu() {
        this.props.onActivation(this.revision.nextRevisionId);
        const { x, y, height } = this.menuButtonRef.el.getBoundingClientRect();
        this.menuState.isOpen = true;
        this.menuState.position = { x, y: y + height };
    }

    closeMenu() {
        this.menuState.isOpen = false;
        this.menuState.position = null;
    }

    formatRevisionTimeStamp(ISOdatetime) {
        const code = pyToJsLocale(this.env.model.getters.getLocale().code);
        return formatToLocaleString(ISOdatetime, code);
    }
}
