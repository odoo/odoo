import { Component, onMounted, onWillStart } from "@odoo/owl";
import { useCamera } from "@hr_attendance/components/hooks/use_camera";

export class AttendanceVideoStream extends Component {
    static template = "hr_attendance.AttendanceVideoStream";
    static props = {
        height: { type: Number },
        width: { type: Number },
        expose: { type: Function, optional: true },
    };

    setup() {
        this.camera = useCamera({
            width: this.props.width,
            height: this.props.height,
        });
        this.streamAvailable = false;

        onWillStart(async () => {
            await this.camera.start();
            this.streamAvailable = this.camera.isStreamAvailable();
        });
        onMounted(async () => {
            this.videoEl = document.getElementById("attendance_video_stream");
            await this.camera.attachStreamToVideo(this.videoEl);
            if (this.props.expose) {
                this.props.expose({
                    capture: () => this.camera.capturePicture(),
                    stop: () => this.camera.stop(),
                });
            }
        });
    }
}
