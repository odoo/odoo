odoo.define('point_of_sale.tour.ClientListScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickClient(name) {
            return [
                {
                    content: `click client '${name}' from client list screen`,
                    trigger: `.clientlist-screen .client-list-contents .client-line td:contains("${name}")`,
                },
                {
                    content: `check if client '${name}' is highlighted`,
                    trigger: `.clientlist-screen .client-list-contents .client-line.highlight td:contains("${name}")`,
                    run: () => {},
                },
            ];
        }
        clickSet() {
            return [
                {
                    content: 'check if set button shown',
                    trigger: '.clientlist-screen .button.next.highlight',
                    run: () => {},
                },
                {
                    content: 'click set button',
                    trigger: '.clientlist-screen .button.next.highlight',
                },
            ];
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'client list screen is shown',
                    trigger: '.pos-content .clientlist-screen',
                    run: () => {},
                },
            ];
        }
    }

    class Execute {
        setClient(name) {
            const steps = [];
            steps.push(...this._do.clickClient(name));
            steps.push(...this._do.clickSet());
            return steps;
        }
    }

    return createTourMethods('ClientListScreen', Do, Check, Execute);
});
