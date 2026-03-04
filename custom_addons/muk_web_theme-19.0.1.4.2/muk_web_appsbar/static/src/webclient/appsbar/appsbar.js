import { url } from '@web/core/utils/urls';
import { useService } from '@web/core/utils/hooks';
import { user } from "@web/core/user";

import { Component, onWillUnmount } from '@odoo/owl';

export class AppsBar extends Component {
	static template = 'muk_web_appsbar.AppsBar';
    static props = {};
	setup() {
        this.appMenuService = useService('app_menu');
    	if (user.activeCompany.has_appsbar_image) {
            this.sidebarImageUrl = url('/web/image', {
                model: 'res.company',
                field: 'appbar_image',
                id: user.activeCompany.id,
            });
    	}
    	const renderAfterMenuChange = () => {
            this.render();
        };
        this.env.bus.addEventListener(
        	'MENUS:APP-CHANGED', renderAfterMenuChange
        );
        onWillUnmount(() => {
            this.env.bus.removeEventListener(
            	'MENUS:APP-CHANGED', renderAfterMenuChange
            );
        });
    }
    _onAppClick(app) {
        return this.appMenuService.selectApp(app);
    }
}
