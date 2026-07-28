/** @odoo-module */
import {Component, useState, mount, xml} from '@odoo/owl';

// Minimalistic placeholder, real use: integrate umalqura & a hijri widget
export class HijriDatepicker extends Component {
    static template = xml`
        <div class="saudi-hijri-datepicker">
            <label t-att-for="props.name"><t t-esc="props.label"/></label>
            <input type="text" t-att-name="props.name" class="form-control" dir="rtl" placeholder="YYYY/MM/DD"/>
        </div>
    `;
}
