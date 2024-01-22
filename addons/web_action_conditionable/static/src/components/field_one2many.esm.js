/** @odoo-module **/
import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {XMLParser} from "@web/core/utils/xml";
import {evaluateExpr} from "@web/core/py_js/py";
import {patch} from "@web/core/utils/patch";

patch(X2ManyField.prototype, "web_action_conditionable_FieldOne2Many", {
    get rendererProps() {
        this.updateActiveActions();
        return this._super(...arguments);
    },
    updateActiveActions() {
        if (this.viewMode === "list" && this.activeActions.type === "one2many") {
            const self = this;
            const parser = new XMLParser();
            const archInfo = this.activeField.views[this.viewMode];
            const xmlDoc = parser.parseXML(archInfo.__rawArch);
            ["create", "delete"].forEach(function (item) {
                if (self.activeActions[item] && _.has(xmlDoc.attributes, item)) {
                    const expr = xmlDoc.getAttribute(item);
                    try {
                        self.activeActions[item] = evaluateExpr(
                            expr,
                            self.props.record.data
                        );
                    } catch (ignored) {
                        console.log(
                            "[web_action_conditionable] unrecognized expr '" +
                                expr +
                                "', ignoring"
                        );
                    }
                }
            });
        }
    },
});
