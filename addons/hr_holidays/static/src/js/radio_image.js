/** @odoo-module **/

import { FieldRadio } from 'web.relational_fields';
import FieldRegistry from 'web.field_registry';

import Core from 'web.core';
const QWeb = Core.qweb;

const FieldRadioImage = FieldRadio.extend({
    _render() {
        const self = this;
        let currentValue;
        if (this.field.type === 'many2one') {
            currentValue = this.value && this.value.data.id;
        } else {
            currentValue = this.value;
        }
        this.$el.empty();
        this.$el.attr('role', 'radiogroup')
            .attr('aria-label', this.string);
        _.each(this.values, function (value, index) {
            if (self.mode === 'edit' || value[0] === currentValue) {
                self.$el.append(QWeb.render('FieldRadioIcon.button', {
                    checked: value[0] === currentValue,
                    id: self.unique_id + '_' + value[0],
                    index: index,
                    name: self.unique_id,
                    value: value,
                    disabled: self.hasReadonlyModifier,
                    mode: self.mode,
                }));
            }
        });
    }
});

FieldRegistry.add('radio_image', FieldRadioImage);
