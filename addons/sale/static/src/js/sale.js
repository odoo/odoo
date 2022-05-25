odoo.define('sale.sales_team_dashboard', function (require) {
"use strict";

const { FieldProgressBar } = require('web.basic_fields');
const fieldRegistry = require('web.field_registry');

var core = require('web.core');
var _t = core._t;

const SalesTeamProgressBar = FieldProgressBar.extend({
    _render() {
        this._super.apply(this, arguments);
        const isUnset = !this.recordData[this.nodeOptions.max_value];
        if (isUnset) {
            const msg = document.createElement('a');
            msg.innerText = _t("Click to define an invoicing target");
            msg.setAttribute('href', '#')
            msg.addEventListener("click", (ev) => {
                ev.preventDefault();
                msg.parentElement.removeChild(msg);
                for (let child of this.el.children) {
                    child.classList.remove('d-none') 
                }
            });
            for (let child of this.el.children) {
                child.classList.add('d-none');
            }
            this.el.insertBefore(msg, this.el.firstChild)
        }
    },
});

fieldRegistry.add("sales_team_progressbar", SalesTeamProgressBar);
});
