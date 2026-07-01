import { Component, onMounted, onWillStart, onWillUnmount, signal } from "@odoo/owl";
import { useCamera } from "@hr_attendance/components/hooks/use_camera";

export class AttendanceVideoStream extends Component {
    static template = "hr_attendance.AttendanceVideoStream";
    static props = {
        height: { type: Number },
        width: { type: Number },
        exposeCameraCapture: { type: Function },
        onStreamStateChange: { type: Function },
    };

    attendanceVideoRef = signal(null);

    setup() {
        this.camera = useCamera({
            width: this.props.width,
            height: this.props.height,
        });

        onWillStart(async () => {
            await this.camera.start();
            this.streamAvailable = this.camera.isStreamAvailable();
        });

        onMounted(async () => {
            this.props.onStreamStateChange(this.streamAvailable);
            if (this.streamAvailable) {
                this.props.exposeCameraCapture(this.camera.capturePicture);
            }
            await this.camera.attachStreamToVideo(this.attendanceVideoRef());
        });

        onWillUnmount(() => {
            this.camera.stop();
            this.props.exposeCameraCapture(null);
            this.props.onStreamStateChange(false);
        });
    }
}
