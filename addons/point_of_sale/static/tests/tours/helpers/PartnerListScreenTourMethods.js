odoo.define('point_of_sale.tour.PartnerListScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickPartner(name) {
            return [
                {
                    content: `click partner '${name}' from partner list screen`,
                    trigger: `.partnerlist-screen .partner-list-contents .partner-line td:contains("${name}")`,
                },
                {
                    content: `check if partner '${name}' is highlighted`,
                    trigger: `.partnerlist-screen .partner-list-contents .partner-line.highlight td:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
        clickSet() {
            return [
                {
                    content: 'check if set button shown',
                    trigger: '.partnerlist-screen .button.next.highlight',
                    run: () => {},
                },
                {
                    content: 'click set button',
                    trigger: '.partnerlist-screen .button.next.highlight',
                },
            ];
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'partner list screen is shown',
                    trigger: '.pos-content .partnerlist-screen',
                    run: () => {},
                },
            ];
        }
    }

    class Execute {
        setPartner(name) {
            const steps = [];
            steps.push(...this._do.clickPartner(name));
            steps.push(...this._do.clickSet());
            return steps;
        }
    }

    return createTourMethods('PartnerListScreen', Do, Check, Execute);
});
