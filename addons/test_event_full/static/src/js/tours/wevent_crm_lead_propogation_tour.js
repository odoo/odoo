import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('wevent_crm_lead_propagation', {
    steps: () => [{
        content: 'Open ticket modal',
        trigger: 'button.btn-primary:contains("Register")',
        run: 'click',
    }, {
        content: 'Add ticket by clicking the '+' button',
        trigger: 'button[data-increment-type*="plus"]',
        run: 'click',
    }, {
        content: 'Click on Register button',
        trigger: '#o_wevent_tickets .btn-primary:contains("Register"):not(:disabled)',
        run: 'click',
    }, {
        content: 'Wait the modal is shown before continue',
        trigger: '.modal.modal_shown.show form[id=attendee_registration]',
    }, {
        content: 'Fill Name',
        trigger: '.modal input[name*="1-name"]',
        run: 'edit Red',
    }, {
        content: 'Fill Email',
        trigger: '.modal input[name*="1-email"]',
        run: 'edit redx@test.example.com',
    }, {
        content: 'Fill Copmany Name',
        trigger: '.modal input[name*="1-company_name"]',
        run: 'edit RedX Studios',
    }, {
        content: 'Submit details',
        trigger: 'button[type=submit]:last',
        run: 'click',
        expectUnloadPage: true,
    }, {
        trigger: 'h1:contains(Registration confirmed!)',
    }]
});
