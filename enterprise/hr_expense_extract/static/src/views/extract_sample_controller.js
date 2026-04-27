import { FormController } from "@web/views/form/form_controller";
import { cookie } from "@web/core/browser/cookie";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

const VIDEO_WIDTH = 300
const VIDEO_HEIGHT = 360;

export class ExtractSampleFormController extends FormController {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.actionService = useService("action");

        onMounted(() => {
            const dialog = document.getElementsByClassName("o_dialog")[0];
            dialog.style.display = "none";

            this.showAnimation();
        });
    }

    get animationSource() {
        return cookie.get("color_scheme") === "dark" ? "/hr_expense_extract/static/img/sample_animation_dark.webm" : "/hr_expense_extract/static/img/sample_animation.webm";
    }

    showAnimation() {
        const content = document.getElementsByClassName("o_content")[0];

        const videoOverlay = document.createElement("div");
        videoOverlay.className = "o_extract_sample_animation_overlay position-absolute top-0 end-0 bottom-0 start-0 d-flex justify-content-center align-items-center bg-100";

        const video = document.createElement("video");
        video.width = VIDEO_WIDTH;
        video.height = VIDEO_HEIGHT;

        const source = document.createElement("source");
        source.src = this.animationSource;
        source.type = "video/webm";

        video.append(source);
        videoOverlay.append(video);
        content.append(videoOverlay);

        setTimeout(() => {
            videoOverlay.classList.add("opacity-100");

            setTimeout(() => {
                video.play();

                setTimeout(async () => {
                    const action = await this.orm.call(
                        "expense.sample.receipt",
                        "action_choose_sample",
                        [this.props.resId]
                    );

                    this.actionService.doAction(action);
                }, 2400); // Delay for the animation to finish and redirect
            }, 400); // Delay for the video to start
        }, 10); // Delay for the fade in to start
    }
}
