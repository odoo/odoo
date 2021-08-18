odoo.define('point_of_sale.ReferenceClientListScreen', function(require) {
    'use strict';

    const { debounce } = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    class ReferenceClientListScreen extends PosComponent{
        constructor(){
            super(...arguments);
            this.state = {
                query: null,
                selectedDoctor: this.props.doctor,
                selectedRefClient: '',
                detailIsShown: false,
            };
            this.updateClientList = debounce(this.updateClientList, 70);
        }
        back(){
            if(this.state.detailIsShown){
                this.state.detailIsShown = false;
                this.render();
            }else{
                this.props.resolve({ confirmed: false, payload: false });
                this.trigger('close-temp-screen');
            }
        }
        confirm(){
            if(this.props.flag == 'show_doctor'){
                this.env.pos.get_order().set_doctor(this.state.selectedDoctor)
                this.props.resolve({ confirmed: true, payload: this.state.selectedDoctor });
            }else{
                this.props.resolve({ confirmed: true, payload: this.state.selectedRefClient });
            }
            this.trigger('close-temp-screen');
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get clients() {
            if (this.state.query && this.state.query.trim() !== ''){
                let searched_result = this.env.pos.db.search_partner(this.state.query.trim());
                if(this.props.flag == 'show_doctor'){
                    return searched_result.filter(partner => partner.is_doctor == true);
                }else{
                    return searched_result
                }
            }else {
                let partners = this.env.pos.db.get_partners_sorted(1000)
                if(this.props.flag == 'show_doctor'){
                    return partners.filter(partner => partner.is_doctor == true);
                }else{
                    return partners
                }
            }
        }
        get isNextButtonVisible(){
            if(this.props.flag == 'show_doctor'){
                return this.state.selectedDoctor ? true : false;
            }else{
                return this.state.selectedRefClient ? true : false;
            }
        }
        get nextButton() {
            if (this.props.client && this.props.client === this.state.selectedRefClient && !this.props.flag) {
                alert('Cannot Select Reference Customer Same As Current Order Customer !!!!');
                return;
            }else if (this.props.doctor && this.props.doctor === this.state.selectedDoctor){
                return { command: 'deselect', text: 'Deselect Doctor' };
            }else {
                if(this.props.flag == 'show_doctor'){
                    return { command: 'set', text: 'Set Doctor' };
                }else{
                    return { command: 'set', text: 'Set Reference Customer' };
                }
            }
        }
        updateClientList(event){
            this.state.query = event.target.value;
            const clients = this.clients;
            if (event.code === 'Enter' && clients.length === 1) {
                if(this.props.flag == 'show_doctor'){
                    this.state.selectedDoctor = clients[0];
                }else{
                    this.state.selectedRefClient = clients[0];
                }
                this.clickNext();
            } else {
                this.render();
            }
        }
        clickClient(event){
            let partner = event.detail.client;
            if(this.props.flag == 'show_doctor'){
                if(this.state.selectedDoctor === partner){
                    this.state.selectedDoctor = null;
                }else{
                    this.state.selectedDoctor = partner;
                }
            }else{
                if(this.state.selectedRefClient === partner){
                    this.state.selectedRefClient = null;
                }else{
                    this.state.selectedRefClient = partner;
                }
            }
            this.render();
        }
        clickNext() {
            this.state.selectedRefClient = this.nextButton.command === 'set' ? this.state.selectedRefClient : null;
            this.state.selectedDoctor = this.nextButton.command === 'set' ? this.state.selectedDoctor : null;
            this.confirm();
        }
    }
    ReferenceClientListScreen.template = 'ReferenceClientListScreen';

    Registries.Component.add(ReferenceClientListScreen);

    return ReferenceClientListScreen;
});
