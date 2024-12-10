import { Component, useState, onWillStart, useEffect } from "@odoo/owl";

import publicWidget from '@web/legacy/js/public/public_widget';
import { Dialog } from '@web/core/dialog/dialog';
import { rpc } from "@web/core/network/rpc";

export class AttValueDialog extends Component {
    static components = { Dialog };
    static template = "website_sale.att_value_dialog";
    static props = [
        "attributeId",
        "attributeName",
        "availableAttributeValues",
        "attribSet",
        "sessionAttValues"
    ];

    setup() {
        this.state = useState({
            attributeValues: [],
            searchInput: "",
            searchDomain: [],
        });
        this.placeholder = `Search ${this.props.attributeName}`;

        onWillStart(() => {
            this._fetchAttibuteValues();
        });

        useEffect(() => {
            const updateModalPosition = () => {
                const targetElement = document.querySelector(
                    `#o_products_attributes_${this.props.attributeId}`
                );
                const modal = document.querySelector(".att-value-dialog .modal");
                const modalContent = modal?.querySelector(".modal-content");

                if (targetElement && modal && modalContent) {
                    const targetRect = targetElement.getBoundingClientRect();
                    const modalContentRect = modalContent.getBoundingClientRect();
                    const modalRect = modal.getBoundingClientRect();

                    const offsetX = modalContentRect.left - modalRect.left;
                    const offsetY = modalContentRect.top - modalRect.top;

                    modal.style.top = `${targetRect.top - offsetY}px`;
                    modal.style.left = `${targetRect.left - offsetX}px`;
                }
            };

            if( window.matchMedia("(min-width: 992px)").matches){
                updateModalPosition();
            }

            window.addEventListener('scroll', updateModalPosition);

            return () => {
                window.removeEventListener('scroll', updateModalPosition);
            };
        });
    }

    async _fetchAttibuteValues() {
        const domain = [['attribute_id', '=', this.props.attributeId], ...this.state.searchDomain];
        const attributeValues = await rpc("/shop/attribute_values", { domain });
        this.state.attributeValues = attributeValues.filter(attributeValue =>
            this.props.availableAttributeValues.includes(attributeValue.id)
        );
    }

    async onSearchInput(ev) {
        this.state.searchInput = ev.target.value;
        this.state.searchDomain = this.state.searchInput
            ? [['name', 'ilike', this.state.searchInput]]
            : [];
        await this._fetchAttibuteValues();
    }

    _onLabelClick(checkboxId) {
        const checkbox = document.querySelector(`.att-value-dialog [id="${checkboxId}"]`);
        if (checkbox && checkbox.type === 'checkbox') {
            checkbox.checked = !checkbox.checked;
        }
    }

    _applyFilters(ev) {
        if (!ev.defaultPrevented) {
            ev.preventDefault();
            ev.currentTarget.parentElement.parentElement.querySelector("form").submit();
        }
    }
}

publicWidget.registry.AttValueDialog = publicWidget.Widget.extend({
    selector: '.view_more',
    events: {
        'click .view_more_btn': '_onClickViewMore',
    },

    _onClickViewMore(ev) {
        const attributeId = parseInt(ev.currentTarget.dataset.attributeId);
        const attributeName = ev.currentTarget.dataset.attributeName;
        const availableAttributeValues = JSON.parse(ev.currentTarget.dataset.availableAttributeValues || "[]");
        const attribSet = JSON.parse(ev.currentTarget.dataset.attribSet || "[]");
        const sessionAttValues = JSON.parse(ev.currentTarget.dataset.sessionAttValues || "[]");
        this.call("dialog", "add", AttValueDialog, {
            attributeId,
            attributeName,
            availableAttributeValues,
            attribSet,
            sessionAttValues
        });
    },
});
