import { registry } from "@web/core/registry";

import { Component } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { Setting } from "@web/views/form/setting/setting";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

/**
 * Widget in the settings that displays links to the mobile apps.
 * As a QRCode in Desktop mode, as an image in mobile mode.
 * Both are clickable links.
 */
class MobileAppsFunnel extends Component {
    static template = "web.MobileAppsFunnel";
    static components = {
        Setting,
    };
    static props = { ...standardWidgetProps };
    setup() {
        this.iosAppstoreImagePath = isMobileOS()
            ? "/web/static/img/app_store.png"
            : "/web/static/img/mobile_app_qrcode_ios.svg";
        this.androidAppstoreImagePath = isMobileOS()
            ? "/web/static/img/google_play.png"
            : "/web/static/img/mobile_app_qrcode_android.svg";
    }
}

export const mobileAppsFunnel = {
    component: MobileAppsFunnel,
};

registry.category("view_widgets").add("mobile_apps_funnel", mobileAppsFunnel);
