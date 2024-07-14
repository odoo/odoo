/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";

export class VisitorForm extends Component {
    setup() {
        this.inputNameRef = useRef("inputName");
        this.inputPhoneRef = useRef("inputPhone");
        this.inputEmailRef = useRef("inputEmail");
        this.inputCompanyRef = useRef("inputCompany");
        this.props.updatePlannedVisitors();
        onMounted(() => {
            this.inputNameRef.el.focus();
        });
        onWillUnmount(() => {
            this.props.clearUpdatePlannedVisitors();
        });
    }

    /**
     * @private
     */
    _onSubmit() {
        this.props.setVisitorData(
            this.inputNameRef.el.value,
            this.inputPhoneRef.el?.value || false,
            this.inputEmailRef.el?.value || false,
            this.inputCompanyRef.el?.value || false
        );
        // Show the HostPage component, if the host_selection field is true from the backend
        this.props.stationInfo.host_selection
            ? this.props.showScreen("HostPage")
            : this.props.showScreen("RegisterPage");
    }
}

VisitorForm.template = "frontdesk.VisitorForm";
VisitorForm.props = {
    clearUpdatePlannedVisitors: Function,
    currentComponent: String,
    currentLang: String,
    isMobile: Boolean,
    isPlannedVisitors: Boolean,
    langs: [Object, Boolean],
    onChangeLang: Function,
    setVisitorData: Function,
    showScreen: Function,
    stationInfo: Object,
    updatePlannedVisitors: Function,
    visitorData: [Object, Boolean],
    theme: String,
};

registry.category("frontdesk_screens").add("VisitorForm", VisitorForm);
