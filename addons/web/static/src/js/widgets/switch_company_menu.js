odoo.define('web.SwitchCompanyMenu', function(require) {
"use strict";

/**
 * When Odoo is configured in multi-company mode, users should obviously be able
 * to switch their interface from one company to the other.  This is the purpose
 * of this widget, by displaying a dropdown menu in the systray.
 */

const config = require('web.config');
const { blockUI } = require('web.framework');
const session = require('web.session');
const SystrayMenu = require('web.SystrayMenu');
const Widget = require('web.Widget');

const { WidgetAdapterMixin, ComponentWrapper } = require('web.OwlCompatibility');

const { useState } = owl.hooks;

class SwitchCompanyListComponent extends owl.Component {

    /**
     * Check if the company is selected
     * @param {number} companyId
     * @returns {boolean}
     */
    _isCompanySelected(companyId) {
        return this.props.allowedCompanyIds.includes(companyId);
    }

    /**
     * Check if the company is the main company
     * @param {number} companyId
     * @returns {boolean}
     */
    _isMainCompany(companyId) {
        return this.props.mainCompanyId === companyId;
    }
    /**
     * Set the company as the main company.
     * If there we are in single company mode (only one company enabled), disable the
     * current main company.
     * @param {number} companyId
     */
    _setMainCompany(companyId) {
        if (this._isMainCompany(companyId)) {
            return;
        }
        this.trigger('main-company-set', { companyId });
    }

    /**
     * Toggle a company as an allowed company.
     * @param {number} companyId
     */
    _toggleCompany(companyId) {
        const event = this._isCompanySelected(companyId) ? 'company-disabled' : 'company-enabled';
        this.trigger(event, { companyId });
    }

    /**
     * @param {number} companyId
     * @param {KeyEvent} ev
     */
    _onKeyDownToggleCompany(companyId, ev) {
        if (ev.code === "Enter" || ev.code === "Space") {
            this._toggleCompany(companyId);
        }
    }

    /**
     * @param {number} companyId
     * @param {KeyEvent} ev
     */
    _onKeyDownSetMainCompany(companyId, ev) {
        if (ev.code === "Enter" || ev.code === "Space") {
            this._setMainCompany(companyId);
        }
    }

}
SwitchCompanyListComponent.props = {
    allowedCompanyIds: Array,
    mainCompanyId: Number,
    dropdownMenu: { type: Boolean, optional: true },
    userCompanies: { type: Array, element: {type: Array} },
};

class SwitchCompanyComponent extends owl.Component {

    constructor() {
        super(...arguments);
        this.state = useState({
            isMobile: config.device.isMobile,
        });
    }

}
SwitchCompanyComponent.components = { SwitchCompanyListComponent };
SwitchCompanyComponent.props = {
    allowedCompanyIds: Array,
    mainCompanyName: String,
    mainCompanyId: Number,
    userCompanies: {
        type: Array,
        element: {type: Array /* [id, name] */}
    },
};

const SwitchCompanyMenu = Widget.extend(WidgetAdapterMixin, {
    componentClass: SwitchCompanyComponent,
    custom_events: Object.assign({}, Widget.prototype.custom_events, WidgetAdapterMixin.custom_events, {
        company_enabled: '_onCompanyEnabled',
        company_disabled: '_onCompanyDisabled',
        main_company_set: '_onMainCompanySet',
    }),
    // force this item to be the first one to the left of the UserMenu in the systray
    sequence: 1,

    willStart() {
        const allowedCompanyIds = String(session.user_context && session.user_context.allowed_company_ids || '')
                                    .split(',')
                                    .map((id) => parseInt(id));
        const mainCompanyId = allowedCompanyIds.length ? allowedCompanyIds[0] : [];
        const userCompanies = session.user_companies && session.user_companies.allowed_companies || [];

        // All companies available to the user
        // Array of Arrays [company id, company name]
        this.userCompanies = userCompanies;

        // Enabled companies
        // Array of ids, the first id is the main company
        this.allowedCompanyIds = allowedCompanyIds;

        this.mainCompanyId = mainCompanyId;
        this.mainCompanyName = mainCompanyId ? this._getCompanyName(mainCompanyId) : '';
        return this._super(...arguments);
    },

    async start() {
        await this._super(...arguments);
        this.component = new ComponentWrapper(this, this.componentClass, this._getComponentProps());
        await this.component.mount(this.el);
        this._replaceElement(this.component.el);
    },

    destroy() {
        this._super(...arguments);
        WidgetAdapterMixin.destroy.call(this, ...arguments);
    },

    /**
     * Return allowed companies except `companyId`
     * @param {number} companyId
     * @returns {number[]}
     */
    _allowedCompanyIdsWithout(companyId) {
        return this.allowedCompanyIds.filter(cid => cid !== companyId);
    },

    /**
     * Returns props required by the OWL component.
     * @returns {object}
     */
    _getComponentProps() {
        return  {
            userCompanies: this.userCompanies,
            allowedCompanyIds: this.allowedCompanyIds,
            mainCompanyName: this.mainCompanyName,
            mainCompanyId: this.mainCompanyId,
        };
    },

    /**
     * Update the OWL component with new company values and save them in the session
     * @returns {Promise}
     */
    async _dispatchCompanyChanges() {
        await this.component.update(this._getComponentProps());
        this._setSessionCompanies();
    },

    _setSessionCompanies: _.debounce(function () {
        blockUI();
        session.setCompanies(this.mainCompanyId, this.allowedCompanyIds);
    }, 1000),

    /**
     * Returns the company name
     * @param {number} companyId
     * @returns {string}
     */
    _getCompanyName(companyId) {
        return this.userCompanies.find(c => c[0] == companyId)[1];
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {object} data
     * @param {number} data.companyId
     * @returns {Promise}
     */
    _onCompanyEnabled({ data }) {
        const { companyId } = data;
        this.allowedCompanyIds = [...this.allowedCompanyIds, companyId];
        return this._dispatchCompanyChanges();
    },

    /**
     * @private
     * @param {object} data
     * @param {number} data.companyId
     * @returns {Promise}
     */
    _onCompanyDisabled({ data }) {
        const { companyId } = data;
        if (this.allowedCompanyIds.length <= 1) return Promise.resolve();
        this.allowedCompanyIds = this._allowedCompanyIdsWithout(companyId);
        if (!this.allowedCompanyIds.includes(this.mainCompanyId)) {
            this.mainCompanyId = this.allowedCompanyIds[0];
            this.mainCompanyName = this._getCompanyName(this.mainCompanyId);
        }
        return this._dispatchCompanyChanges();
    },

    /**
     * @private
     * @param {object} data
     * @param {number} data.companyId
     * @returns {Promise}
     */
    _onMainCompanySet({ data }) {
        const { companyId } = data;
        this.mainCompanyId = companyId;
        this.mainCompanyName = this._getCompanyName(companyId);
        if (this.allowedCompanyIds.length > 1) {
            // multi company mode
            this.allowedCompanyIds = [companyId, ...this._allowedCompanyIdsWithout(companyId)];
        }
        else {
            // 1 enabled company: Stay in single company mode
            this.allowedCompanyIds = [companyId];
        }
        return this._dispatchCompanyChanges();
    },
});

if (session.display_switch_company_menu) {
    SystrayMenu.Items.push(SwitchCompanyMenu);
}

return {
    SwitchCompanyMenu,
    SwitchCompanyComponent,
    SwitchCompanyListComponent,
};

});
