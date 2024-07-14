/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";
import { SignablePDFIframe } from "@sign/components/sign_request/signable_PDF_iframe";
import { EditablePDFIframeMixin } from "@sign/backend_components/editable_pdf_iframe_mixin";

export class EditWhileSigningSignablePDFIframe extends EditablePDFIframeMixin(SignablePDFIframe) {
    toggleSidebar() {
        const sidebar = this.root.querySelector(".o_sign_field_type_toolbar");
        sidebar.classList.toggle("d-none");
    }

    renderSidebar() {
        // add field type toolbar for edit mode while signing
        if (this.allowEdit) {
            const sideBar = renderToString("sign.signItemTypesSidebar", {
                signItemTypes: this.props.signItemTypes.filter(
                    (type) => type.editWhileSigningAllowed
                ),
                sidebarHidden: true,
            });
            this.root.body.insertAdjacentHTML("afterbegin", sideBar);
            this.signRolesById = {};
            this.signRolesById[this.currentRole] = { name: this.props.currentName };
        }
    }

    get allowEdit() {
        return !this.readonly && this.props.templateEditable && !this.env.isSmall;
    }

    registerCloseEvent(signItem) {
        const configArea = signItem.el.querySelector(".o_sign_config_area");
        const closeButton = configArea.querySelector(".fa-times");
        closeButton.addEventListener(
            "click",
            () => {
                this.deleteSignItem(signItem);
                this.checkSignItemsCompletion();
            },
            { once: true }
        );
    }

    showBanner() {
        super.showBanner();
        const nameList = this.signInfo.get("nameList");
        if (nameList && nameList.length > 0) {
            const nextName = nameList[0];
            const bannerTitle = _t("Validate & the next signatory is “%s”", nextName);
            this.props.validateButton.textContent = bannerTitle;
        }
    }

    /**
     * Creates rendering context for the sign item based on the sign item type
     * @param {number} typeId
     * @returns {Object} context
     */
    createSignItemDataFromType(typeId) {
        const type = this.signItemTypesById[typeId];
        return {
            required: true,
            editMode: true,
            readonly: true,
            updated: true,
            isSignItemEditable: true,
            responsible: this.currentRole,
            option_ids: [],
            options: [],
            name: type.name,
            width: type.defaultWidth,
            height: type.defaultHeight,
            alignment: "center",
            type: type.item_type,
            placeholder: type.placeholder,
            classes: "o_sign_sign_item_required",
            style: `width: ${type.defaultWidth * 100}%; height: ${type.defaultHeight * 100}%;`,
            type_id: type.id,
        };
    }

    enableCustom(signItem) {
        super.enableCustom(signItem);
        if (signItem.data.isSignItemEditable) {
            this.registerCloseEvent(signItem);
        }
    }
}
