import options from "@web_editor/js/editor/snippets.options";

options.registry.websiteDynamicEmployeeCard = options.Class.extend({
    /**
     * sets the department domain
     */
    setDepartment(previewMode, widgetValue, params) {
        return (
            this.$target[0].setAttribute("data-department", widgetValue) || ""
        );
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === "setDepartment") {
            return this.$target[0].getAttribute("data-department") || "";
        }
        return this._super(...arguments);
    },
});
