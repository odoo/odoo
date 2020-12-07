/** @odoo-module alias=web.web_client **/

import env from 'web.env';
import WebClient from 'web.AbstractWebClient';
import AbstractService from 'web.AbstractService';
import PointOfSaleUI from 'point_of_sale.PointOfSaleUI';
import PointOfSaleModel from 'point_of_sale.PointOfSaleModel';

owl.config.mode = env.isDebug() ? 'dev' : 'prod';
owl.Component.env = env;

const SEARCH_LIMIT = 1000;

async function setup(webClient) {
    // Publish a singleton posmodel
    env.model = new PointOfSaleModel(webClient, SEARCH_LIMIT);

    // Setup responsive
    const isMobile = () => window.innerWidth <= 768;
    env.isMobile = isMobile();
    const updateEnv = owl.utils.debounce(() => {
        if (env.isMobile !== isMobile()) {
            env.isMobile = !env.isMobile;
            env.qweb.forceUpdate();
        }
    }, 15);
    window.addEventListener('resize', updateEnv);

    // Setup owl
    await env.session.is_bound;
    env.qweb.addTemplates(env.session.owlTemplates);
    env.bus = new owl.core.EventBus();
    await owl.utils.whenReady();

    // Setup webclient needed for tour
    await webClient.setElement(document.body);
    await webClient.start();
    webClient.isStarted = true;

    // Start POS Component
    const posui = new PointOfSaleUI();
    await posui.mount(document.querySelector('.o_action_manager'));

    const syncNotification = posui.syncNotificationRef.comp;
    const posDialog = posui.posDialogRef.comp;
    const toastNotification = posui.toastNotificationRef.comp;
    const notificationSound = posui.notificationSoundRef.comp;

    // This will contain ui controls that can be useful in the model via `this.ui`.
    // They can also be accessed in each component via `this.env.ui`.
    const ui = {
        setSyncStatus: syncNotification.setSyncStatus.bind(syncNotification),
        askUser: posDialog.askUser.bind(posDialog),
        showNotification: toastNotification.showNotification.bind(toastNotification),
        playSound: notificationSound.playSound.bind(notificationSound),
    };

    env.ui = ui;
    env.model.ui = ui;
    window.posmodel = env.model;
}

AbstractService.prototype.deployServices(env);
const webClient = new WebClient();
setup(webClient);
export default webClient;
