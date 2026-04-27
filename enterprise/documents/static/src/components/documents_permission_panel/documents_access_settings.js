/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { DocumentsPermissionSelect } from "./documents_permission_select";
import { Component } from "@odoo/owl";

const accessProps = {
    access_internal: String,
    access_via_link: String,
    is_access_via_link_hidden: Boolean,
};

export class DocumentsAccessSettings extends Component {
    static components = {
        CheckBox,
        DocumentsPermissionSelect,
    };
    static props = {
        access: accessProps,
        baseAccess: accessProps,
        disabled: Boolean,
        onChangeAccessInternal: Function,
        onChangeAccessLink: Function,
        onChangeIsAccessLinkHidden: Function,
        selections: Object,
    };
    static template = "documents.AccessSettings";

    /**
     * Return additional label corresponding to internal access setting
     */
    get accessInternalHelper() {
        if (this.props.access.access_internal === "view") {
            return _t("Internal users can view");
        }
        if (this.props.access.access_internal === "edit") {
            return _t("Internal users can edit");
        }
        return _t("Only people with access can open with the link");
    }

    /**
     * Return additional label corresponding to link access setting
     */
    get accessLinkHelper() {
        if (this.props.access.access_via_link === "view") {
            return _t("Anyone on the internet with the link can view");
        }
        if (this.props.access.access_via_link === "edit") {
            return _t("Anyone on the internet with the link can edit");
        }
        return _t("No one on the internet can access");
    }

    /**
     * Return an error message to disable the edit mode.
     */
    get errorAccessLinkEdit() {
        return undefined;
    }

    /**
     * Return an error message to disable the edit mode.
     */
    get errorAccessInternalEdit() {
        return undefined;
    }
}
