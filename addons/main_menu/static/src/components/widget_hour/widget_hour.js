import { Component, useState, onWillUnmount } from "@odoo/owl";
import { user } from "@web/core/user";

export class WidgetHour extends Component {
    static template = "main_menu.WidgetHour";
    static props = {
        userIsAdmin: Boolean,
        announcement: String,
    };

    setup(){
        const lang = user.context.lang.replace("_", "-");
        this.state = useState({
            currentTime: this._getTime(),
            currentDate: this._getDate(lang),
        });

        this.interval = setInterval(() => {
            this.state.currentDate = this._getDate(lang);
            this.state.currentTime = this._getTime();
        }, 1000);

        onWillUnmount(() => {
            clearInterval(this.interval);
        });
    }

    _getDate(lang) {
        try {
            return new Date().toLocaleDateString(lang, {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric"
            });
        } catch {
            return new Date().toLocaleDateString();
        }
    }

    _getTime() {
        return new Date().toLocaleTimeString();
    }
}

