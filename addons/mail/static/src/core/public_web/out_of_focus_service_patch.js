import { OutOfFocusService, outOfFocusService } from "@mail/core/common/out_of_focus_service";
import { patch } from "@web/core/utils/patch";

patch(OutOfFocusService.prototype, {
    setup(env, services) {
        super.setup(env, services);
        this.counter = 0;
        env.bus.addEventListener("window_focus", () => this.clearUnreadMessage());
    },
    clearUnreadMessage() {
        this.counter = 0;
        this.updateFavicon();
    },
    notify() {
        super.notify(...arguments);
        this.counter++;
        this.updateFavicon();
    },
    updateFavicon() {
        const count = this.counter;
        const favicon =
            document.querySelector("link[rel='shortcut icon']") ??
            document.querySelector("link[rel='icon']");
        if (this.favurl === undefined) {
            this.favurl = favicon.href;
        }
        const canvas = document.createElement("canvas");
        canvas.width = 16;
        canvas.height = 16;
        const context = canvas.getContext("2d");
        const img = document.createElement("img");
        if (favicon === null) {
            return;
        }
        img.src = favicon.href;
        img.onload = () => {
            if (context === null) {
                return;
            }
            context.drawImage(img, 0, 0, 16, 16);
            if (count > 0) {
                context.beginPath();
                context.fillStyle = "#e9ecef";
                if (count < 10) {
                    context.roundRect(9, 6, 6, 12, 1);
                } else {
                    context.roundRect(5, 6, 14, 12, 1);
                }
                context.fill();
                context.font = '11px "helvetica", sans-serif';
                context.textAlign = "center";
                context.textBaseline = "middle";
                context.fillStyle = "#000";
                if (count < 10) {
                    context.fillText(String(count), 12, 12);
                } else {
                    context.fillText(String(count), 10, 12);
                }
                favicon.href = canvas.toDataURL("image/png");
            } else {
                favicon.href = this.favurl;
            }
        };
    },
});
outOfFocusService.dependencies = [...outOfFocusService.dependencies];
