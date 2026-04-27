/** @odoo-module */

import { Component, useRef, useState, useEffect } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { components } from "@odoo/o-spreadsheet";

import { formatToLocaleString } from "../../../helpers/misc";
import { _t } from "@web/core/l10n/translation";
import { pyToJsLocale } from "@web/core/l10n/utils";


export class VersionHistoryItem extends Component {
    static template = "spreadsheet_edition.VersionHistoryItem";
    static components = { Dropdown, TextInput: components.TextInput };
    static props = {
        active: Boolean,
        revision: Object,
        onActivation: Function,
        onBlur: Function,
        getRevisions: Function,
        renameRevision: Function,
        restoreRevision: Function,
        forkHistory: Function,
        getLocale: Function,
        editable: { optional: true, type: Boolean },
    };

    setup() {
        this.menuState = useState({ isOpen: false });
        this.state = useState({ editName: this.defaultName });
        this.menuButtonRef = useRef("menuButton");
        this.itemRef = useRef("item");

        useEffect(() => {
            if (this.props.active) {
                this.itemRef.el.scrollIntoView({
                    behavior: "smooth",
                    block: "nearest",
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

    get formattedTimeStamp() {
        return this.formatRevisionTimeStamp(this.props.revision.timestamp);
    }

    get isLatestVersion() {
        return (
            this.props.getRevisions()[0].nextRevisionId === this.revision.nextRevisionId
        );
    }

    renameRevision(newName) {
        this.state.editName = newName;
        if (!this.state.editName) {
            this.state.editName = this.defaultName;
        }
        if (this.state.editName !== this.defaultName) {
            this.props.renameRevision(this.revision.id, this.state.editName);
        }
    }

    get menuItems() {
        return [
            {
                label: _t("Make a copy"),
                onSelected: () => this.props.forkHistory(this.revision.id),
                id: "copy_" + this.revision.id,
            },
            {
                label: _t("Restore this version"),
                onSelected: () => this.props.restoreRevision(this.revision.id),
                id: "restore_" + this.revision.id,
            },
        ];
    }

    activate() {
        this.props.onActivation(this.revision.nextRevisionId);
    }

    formatRevisionTimeStamp(ISOdatetime) {
        const code = pyToJsLocale(this.props.getLocale().code);
        return formatToLocaleString(ISOdatetime, code);
    }
}
